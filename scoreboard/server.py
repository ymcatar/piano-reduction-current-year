import asyncio
import functools
import glob
import logging
import json
import os
import subprocess

from aiohttp import web
from music21.converter.subConverters import ConverterMusicXML, SubConverterException
from music21 import environment


LOG_DIR = os.path.abspath('log')
PUBLIC_DIR = os.path.abspath('scoreboard/public')

environ_local = environment.Environment('scoreboard/server.py')


def configure_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fmt = '%(asctime)s %(levelname)s %(message)s'
    formatter = logging.Formatter(fmt, datefmt='%H:%M:%S')
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)


run_map = {}
runs = []


@web.middleware
async def cors_middleware(request, handler):
    resp = await handler(request)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


# Add indentation to json_response
json_response = functools.partial(
    web.json_response, dumps=functools.partial(json.dumps, indent=2))


async def update_run_map():
    for run in os.listdir(LOG_DIR):
        if run in run_map:
            continue
        index_path = os.path.join(LOG_DIR, run, 'index.json')
        if not os.path.exists(index_path):
            continue
        try:
            with open(index_path) as f:
                run_data = json.load(f)
            assert type(run_data) == dict
            run_data.update({
                'name': run,
                'path': '{}'.format(run),
                })
            run_map[run] = run_data
        except (OSError, json.JSONDecodeError):
            logging.info('Error loading run {}'.format(run), excinfo=True)
    global runs
    runs = sorted(run_map.values(), key=lambda d: -d['timestamp'])


async def list_runs(request):
    await update_run_map()
    return json_response({'runs': runs})


xml_map = {}


async def ensure_xml_render(path):
    basepath, _ = os.path.splitext(path)
    out_path = basepath + '-index.json'
    if not os.path.exists(out_path):
        try:
            logging.info('Rendering XML: {}'.format(path))
            mscore = environ_local['musescoreDirectPNGPath']
            if not mscore or not os.path.exists(mscore):
                raise web.HTTPInternalServerError('MuseScore not installed')
            subprocess.run([mscore, '-o', path[:-3] + 'svg', '-T', '0', path], check=True)
            full_image_paths = sorted(glob.glob('{}-*.svg'.format(basepath)))
            image_paths = [i.rsplit('/', 1)[1] for i in full_image_paths]

            with open(out_path, 'w') as f:
                data = {
                    'pages': image_paths,
                    }
                try:
                    json.dump(data, f)
                except:
                    os.remove(out_path)
                    raise
        except SubConverterException:
            raise web.HTTPInternalServerError('Error rendering XML')

    return out_path


async def index_xml(request):
    basepath = os.path.join(LOG_DIR, request.match_info['basepath'])
    if not os.path.exists(basepath + '.xml'):
        raise web.HTTPNotFound()

    if basepath not in xml_map:
        xml_map[basepath] = asyncio.ensure_future(ensure_xml_render(basepath + '.xml'))
    if xml_map[basepath].done():
        out_path = xml_map[basepath].result()
    else:
        out_path = await xml_map[basepath]

    return web.FileResponse(out_path)


def main():
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get('/log/index.json', list_runs)
    app.router.add_get(r'/log/{basepath:.*}-index.json', index_xml)
    app.router.add_static('/log/', path=LOG_DIR, name='static')
    # app.router.add_static('/', path=PUBLIC_DIR, name='public')

    web.run_app(app, port=8081)


if __name__ == '__main__':
    configure_logger()
    main()

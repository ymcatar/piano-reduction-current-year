import asyncio
import functools
import glob
import logging
import json
import os

from aiohttp import web
from music21.converter.subConverters import ConverterMusicXML, SubConverterException


LOG_DIR = os.path.abspath('log')
PUBLIC_DIR = os.path.abspath('scoreboard/public')


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
        try:
            with open(os.path.join(LOG_DIR, run, 'index.json')) as f:
                run_data = json.load(f)
            assert type(run_data) == dict
            run_data.update({
                'name': run,
                'path': '{}'.format(run),
                })
            run_map[run] = run_data
        except (OSError, json.JSONDecodeError) as e:
            logging.info('Error loading run {}'.format(run), e)
    global runs
    runs = sorted(run_map.values(), key=lambda d: -d['timestamp'])


async def list_runs(request):
    await update_run_map()
    return json_response({'runs': runs})


async def index_run(request):
    name = request.match_info['name']
    return web.FileResponse(os.path.join(LOG_DIR, name, 'index.json'))


xml_map = {}


async def ensure_xml_render(path):
    basepath, _ = os.path.splitext(path)
    for zeros in range(3):
        if os.path.exists('{}-{}1.png'.format(basepath, '0' * zeros)):
            break
    else:
        try:
            logging.info('Rendering XML: {}'.format(path))
            converter = ConverterMusicXML()
            converter.runThroughMusescore(path)
        except SubConverterException:
            raise web.HTTPInternalServerError('Error rendering XML')

    return sorted(i.rsplit('/', 1)[1] for i in glob.glob('{}-*.png'.format(basepath)))


async def index_xml(request):
    path = os.path.join(LOG_DIR, request.match_info['path'])
    if not os.path.exists(path):
        raise web.HTTPNotFound()

    if path not in xml_map:
        xml_map[path] = asyncio.ensure_future(ensure_xml_render(path))
    if xml_map[path].done():
        pages = xml_map[path].result()
    else:
        pages = await xml_map[path]

    return json_response({'pages': pages})


def main():
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get('/log/', list_runs)
    app.router.add_get(r'/log/{name}/', index_run)
    app.router.add_get(r'/log/{path:.*\.xml}/index', index_xml)
    app.router.add_static('/log/', path=LOG_DIR, name='static')
    # app.router.add_static('/', path=PUBLIC_DIR, name='public')

    web.run_app(app, port=8081)


if __name__ == '__main__':
    configure_logger()
    main()

<template>
  <canvas ref="canvas" @wheel="onWheel" @click="onClick" @mousemove="throttledOnMouseMove"></canvas>
</template>

<script>
// Throttle with requestAnimationFrame
function throttle(fn) {
  let running = false;
  const out = (...args) => {
    if (running) { return; }
    running = true;
    window.requestAnimationFrame(() => {
      running = false;
      fn(...args);
    });
  };
  return out;
}

export default {
  name: 'ScoreCanvas',
  props: ['apiPrefix', 'pages', 'annotations', 'pageOffset'],
  data: () => ({
    canvas: null,
    ctx: null,
    bitmaps: [],
    noteMaps: [],
    pageLoadings: [],
    pageBuffers: {},
    density: null,
    width: null,
    height: null,
    scale: 'fit',

    visiblePages: [],

    drawTimeTotal: 0,
    drawTimeCount: 0,

    throttledOnMouseMove: () => {},
  }),

  computed: {
    realScale() {
      if (this.scale === 'fit') {
        if (!this.bitmaps[0]) return 1;
        let maxBitmapHeight = 0;
        for (const bitmap of this.bitmaps) {
          if (bitmap) maxBitmapHeight = Math.max(maxBitmapHeight, bitmap.height);
        }
        const bitmap = this.bitmaps[0];
        return Math.min(this.width / bitmap.width, this.height / maxBitmapHeight);
      }
      return this.scale * this.density;
    },

    drawTimeAverage() {
      return this.drawTimeTotal / this.drawTimeCount;
    }
  },

  methods: {
    async loadImage(pageIndex) {
      try {
        console.info('Loading', this.pages[pageIndex]);
        this.pageLoadings[pageIndex] = true;
        const src = this.apiPrefix + this.pages[pageIndex];
        const res = await fetch(src);
        if (!res.ok) throw new Error('Response not ok');
        const text = await res.text();
        const div = document.createElement('div');
        div.innerHTML = text;

        const noteMap = {};
        const svg = div.querySelector('svg');
        // Add to DOM so that we can get the bounding box
        document.documentElement.appendChild(svg);
        for (const elem of svg.children) {
          if (!elem.classList.contains('Note')) continue;

          const ctm = elem.getCTM();
          const bBox = elem.getBBox();
          let s = svg.createSVGPoint(); s.x = bBox.x; s.y = bBox.y;
          s = s.matrixTransform(ctm);

          noteMap[elem.getAttribute('fill').toUpperCase()] = {
            ctm: elem.getCTM(),
            path: elem.getAttribute('d'),
            // Hopefully there are no rotations
            bBox: {x: s.x, y: s.y, width: bBox.width, height: bBox.height},
          };
        }
        document.documentElement.removeChild(svg);

        this.noteMaps[pageIndex] = noteMap;

        this.bitmaps[pageIndex] = await new Promise((resolve, reject) => {
          const img = document.createElement('img');
          img.onload = () => resolve(img);
          img.onerror = (e) => {
            const error = new Error('Error parsing SVG');
            error.error = e;
            reject(error);
          };
          // This loads the image again, but seems to be much more reliable
          // across browsers
          img.src = src;
        });
        // Vue.js sucks? Change detection issue
        this.bitmaps = this.bitmaps.slice();

        // Need to invalidate all because it might trigger resize, and rays are
        // cross-page
        this.invalidateAllBuffers();
        this.draw();
      } catch (err) {
        this.pageLoadings[pageIndex] = false;
        throw err;
      }
      console.log('Loaded', this.pages[pageIndex]);
    },

    ensureLoaded(pageIndex) {
      if (!this.pageLoadings[pageIndex])
        this.loadImage(pageIndex);
    },

    drawPage(pageIndex) {
      if (!this.pageBuffers[pageIndex]) {
        this.pageBuffers[pageIndex] = {
          canvas: document.createElement('canvas'),
          valid: false
        };
      }
      if (this.pageBuffers[pageIndex].valid) return;

      const canvas = this.pageBuffers[pageIndex].canvas;
      const ctx = canvas.getContext('2d');

      if (!this.bitmaps[pageIndex]) {
        this.ensureLoaded(pageIndex);
        return;
      }
      const bitmap = this.bitmaps[pageIndex];
      canvas.width = bitmap.width * this.realScale;
      canvas.height = bitmap.height * this.realScale;

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw page
      ctx.setTransform(this.realScale, 0, 0, this.realScale, 0, 0);
      ctx.drawImage(bitmap, 0, 0, bitmap.width, bitmap.height);

      // Annotations
      const self = this;
      const iterEntries = function*() {
        for (const key in self.noteMaps[pageIndex]) {
          if (!self.noteMaps[pageIndex].hasOwnProperty(key)) continue;
          const entry = self.noteMaps[pageIndex][key];
          const annotation = self.annotations.notes[key];
          if (!annotation) continue;
          yield [entry, annotation];
        }
      };

      // Notehead
      for (const [entry, annotation] of iterEntries()) {
        let colours = [];
        for (let i = 0; i < annotation.noteheads.length; i++) {
          if (annotation.noteheads[i] !== '#000000')
            colours.push(annotation.noteheads[i]);
        }
        if (!colours.length) colours.push('#000000');
        ctx.save();

        let ctm = entry.ctm;
        ctx.transform(ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f);
        ctx.clip(new Path2D(entry.path));
        ctm = ctm.inverse();
        ctx.transform(ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f);

        for (let i = 0; i < colours.length; i++) {
          ctx.fillStyle = colours[i];
          ctx.fillRect(
              entry.bBox.x, entry.bBox.y + entry.bBox.height * i / colours.length,
              entry.bBox.width, entry.bBox.height / colours.length);
        }
        ctx.restore();
      }

      // Text
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 2;
      ctx.font = 'bold 8px Roboto, Noto Sans, sans-serif';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      for (const [entry, annotation] of iterEntries()) {
        if (annotation.rightText) {
          const OFFSET = 1;
          const args = [
            annotation.rightText.text,
            entry.bBox.x + entry.bBox.width + OFFSET,
            entry.bBox.y + 0.5 * entry.bBox.height];
          ctx.fillStyle = annotation.rightText.colour;
          ctx.strokeText(...args);
          ctx.fillText(...args);
        }
      }
      ctx.textBaseline = 'top';
      for (const [entry, annotation] of iterEntries()) {
        if (annotation.bottomText) {
          const OFFSET = 0;
          const args = [
            annotation.bottomText.text,
            entry.bBox.x,
            entry.bBox.y + entry.bBox.height + OFFSET];
          ctx.fillStyle = annotation.bottomText.colour;
          ctx.strokeText(...args);
          ctx.fillText(...args);
        }
      }

      // Shape
      const OFFSET = 2;
      ctx.lineWidth = 2;
      for (const [entry, annotation] of iterEntries()) {
        if (annotation.circle) {
          ctx.strokeStyle = annotation.circle;
          ctx.beginPath();
          ctx.ellipse(
            entry.bBox.x + 0.5 * entry.bBox.width, entry.bBox.y + 0.5 * entry.bBox.height,
            entry.bBox.width / 2 + OFFSET, entry.bBox.height / 2 + OFFSET,
            0, 0, 2*Math.PI);
          ctx.stroke();
        }
      }

      // Ray
      ctx.lineWidth = 1;
      const RADIUS = 4;
      for (const key in this.annotations.structures) {
        if (!this.annotations.structures.hasOwnProperty(key)) continue;
        const [u, v] = key.split(':');
        const entry = this.annotations.structures[key];
        const upos = this.findNoteInPage(u, pageIndex);
        const vpos = this.findNoteInPage(v, pageIndex);
        if (!upos || !vpos) continue;
        if (entry.directed) {
          ctx.fillStyle = entry.colour;
          ctx.beginPath();
          ctx.ellipse(upos.x, upos.y, RADIUS, RADIUS, 0, 0, 2 * Math.PI);
          ctx.fill();
        }
        ctx.strokeStyle = entry.colour;
        ctx.beginPath();
        ctx.moveTo(upos.x, upos.y);
        ctx.lineTo(vpos.x, vpos.y);
        ctx.stroke();
      }

      this.pageBuffers[pageIndex].valid = true;
    },

    draw() {
      const start = Date.now();
      const ctx = this.ctx;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      if (!this.pages) return;
      if (!this.bitmaps[0]) {
        this.ensureLoaded(0);
        return;
      }

      const pageWidth = this.bitmaps.map(b => b ? b.width : 0).slice(0, -1)
          .reduce((a, b) => Math.max(a, b), 0);
      this.visiblePages = [];
      let pageIndex, x;
      for (pageIndex = Math.floor(this.pageOffset),
          x = -pageWidth * (this.pageOffset % 1);
          pageIndex < this.pages.length && x * this.realScale < this.canvas.width;
          pageIndex++, x += pageWidth) {
        if (!this.bitmaps[pageIndex]) {
          this.ensureLoaded(pageIndex);
          continue;
        }

        const pageX = x * this.realScale, pageY = 0;
        this.visiblePages.unshift({pageX, pageY, pageIndex});

        this.drawPage(pageIndex);
        ctx.drawImage(this.pageBuffers[pageIndex].canvas, pageX, pageY);
      }
      if (pageIndex < this.pages.length)
        this.ensureLoaded(pageIndex);

      this.drawTimeTotal += Date.now() - start;
      this.drawTimeCount += 1;
    },

    invalidateAllBuffers() {
      this.pageBuffers = {};
    },

    resize() {
      if (!this.$refs.canvas) return; // Not sure why this happens
      console.info('Resizing');
      let density = window.devicePixelRatio;
      // This avoids ugly aliasing
      if (density === 1) density = 2;
      this.density = density;
      this.width = this.canvas.width = this.$refs.canvas.clientWidth * density;
      this.height = this.canvas.height = this.$refs.canvas.clientHeight * density;
      this.invalidateAllBuffers();
      this.draw();
    },

    onWheel(e) {
      if (!this.pages) return;
      e.preventDefault();
      let delta = e.deltaX || e.deltaY;
      if (e.deltaMode === WheelEvent.DOM_DELTA_LINE)
        delta *= 40;
      let pageOffset = this.pageOffset + delta / 1000;
      pageOffset = Math.min(pageOffset, this.pages.length - 0.5);
      pageOffset = Math.max(pageOffset, 0);
      this.$emit('update:page-offset', pageOffset);
      this.throttledDraw();
    },

    fixPageOffset() {
      let pageOffset = this.pageOffset;
      if (this.pages)
        pageOffset = Math.min(pageOffset, this.pages.length - 0.5);
      pageOffset = Math.max(pageOffset, 0);
      if (this.pageOffset !== pageOffset)
        this.$emit('update:page-offset', pageOffset);
    },

    onClick(e) {
      const matches = this.findNotesByOffset(e.offsetX, e.offsetY);
      if (matches.length) {
        this.$emit('select', matches);
      }
    },

    onMouseMove(e) {
      const matches = this.findNotesByOffset(e.offsetX, e.offsetY);
      this.$emit('hover', {matches, offsetX: e.offsetX, offsetY: e.offsetY});
    },

    findNotesByOffset(offsetX, offsetY) {
      if (!this.pages || !this.bitmaps[0]) return [];
      // Convert to canvas units
      const canvasX = offsetX * this.density, canvasY = offsetY * this.density;

      const match = this.visiblePages.find(p => p.pageX <= canvasX);
      if (!match) return [];

      const pageIndex = match.pageIndex;

      const x = (canvasX - match.pageX) / this.realScale, y = (canvasY - match.pageY) / this.realScale;

      const noteMap = this.noteMaps[pageIndex];
      if (!noteMap) return [];

      const matches = [];
      for (const key in noteMap) {
        if (!this.noteMaps[pageIndex].hasOwnProperty(key)) continue;
        const bBox = this.noteMaps[pageIndex][key].bBox;
        if (bBox.x <= x && x <= bBox.x + bBox.width && bBox.y <= y && y <= bBox.y + bBox.height)
          matches.push(key);
      }
      return matches;
    },

    findNoteInPage(key, currentPageIndex) {
      for (let pageIndex = Math.max(0, currentPageIndex-1);
          pageIndex < Math.min(this.pages.length, currentPageIndex+2);
          pageIndex++) {

        // Calculate page X relative to current page
        let pageX = 0;
        if (pageIndex === currentPageIndex-1) {
          if (!this.bitmaps[pageIndex]) continue;
          pageX = -this.bitmaps[pageIndex].width;
        } else if (pageIndex === currentPageIndex+1) {
          if (!this.bitmaps[currentPageIndex]) continue;
          pageX = this.bitmaps[currentPageIndex].width;
        }

        if (!this.noteMaps[pageIndex]) continue;
        let entry = this.noteMaps[pageIndex][key];
        if (entry) {
          return {
            x: pageX + entry.bBox.x + 0.5 * entry.bBox.width,
            y: entry.bBox.y + 0.5 * entry.bBox.height
          };
        }
      }
      return null;
    },
  },

  watch: {
    pages() {
      this.bitmaps = this.pages.map(() => null);
      this.noteMaps = this.pages.map(() => null);
      this.pageLoadings = this.pages.map(() => false);
      this.resize();
      this.fixPageOffset();
    },

    pageOffset() {
      this.fixPageOffset();
      this.throttledDraw();
    },

    annotations() {
      this.invalidateAllBuffers();
      this.draw();
    },
  },

  mounted() {
    this.ctx = this.$refs.canvas.getContext('2d');
    this.ctx.imageSmoothingQuality = 'high';
    this.canvas = this.$refs.canvas;

    this.throttledResize = throttle(this.resize.bind(this));
    this.throttledDraw = throttle(this.draw.bind(this));
    this.throttledOnMouseMove = throttle(this.onMouseMove.bind(this));

    this.resize();
    this.resizeListener = window.addEventListener('resize', () => this.throttledResize());
  },

  beforeDestroy() {
    window.removeEventListener('resize', this.resizeListener);
  },
};
</script>

<style lang="scss" scoped>
  canvas {
    width: 100%; height: 100%;
  }
</style>

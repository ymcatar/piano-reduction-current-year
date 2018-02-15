<template>
  <canvas ref="canvas" @wheel="onWheel" @click="onClick"></canvas>
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
    ratio: null,
    width: null,
    height: null,
    scale: 'fit',
    pageMargin: 32,

    visiblePages: [],

    drawTimeTotal: 0,
    drawTimeCount: 0,
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
        const effectiveHeight = this.height - this.pageMargin * this.ratio * 2;
        return Math.min(this.width / bitmap.width, effectiveHeight / maxBitmapHeight);
      }
      return this.scale * this.ratio;
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
        const res = await fetch(this.apiPrefix + this.pages[pageIndex]);
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
        global.svg = svg;
        global.noteMap = noteMap;

        this.noteMaps[pageIndex] = noteMap;

        this.bitmaps[pageIndex] = await new Promise((resolve, reject) => {
          const img = document.createElement('img');
          img.onload = () => resolve(img);
          img.onerror = (e) => {
            const error = new Error('Error parsing SVG');
            error.error = e;
            reject(error);
          };
          img.src = 'data:image/svg+xml;utf8,' + text;
        });
        // Vue.js sucks? Change detection issue
        this.bitmaps = this.bitmaps.slice();


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

      const scaledMargin = this.pageMargin * this.ratio;
      const pageWidth = this.bitmaps.map(b => b ? b.width : 0).slice(0, -1)
          .reduce((a, b) => Math.max(a, b), 0);
      console.log(pageWidth);
      this.visiblePages = [];
      let pageIndex, x;
      for (pageIndex = Math.floor(this.pageOffset),
          x = -pageWidth * (this.pageOffset % 1) + scaledMargin;
          pageIndex < this.pages.length && x * this.realScale < this.canvas.width;
          pageIndex++, x += pageWidth + scaledMargin) {
        if (!this.bitmaps[pageIndex]) {
          this.ensureLoaded(pageIndex);
          continue;
        }
        const bitmap = this.bitmaps[pageIndex];

        const pageX = x * this.realScale, pageY = scaledMargin;
        this.visiblePages.unshift({pageX, pageY, pageIndex});

        // Draw page
        ctx.setTransform(this.realScale, 0, 0, this.realScale, pageX, pageY);
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
          let colour = '#000000';
          for (let i = 0; i < annotation.noteheads.length; i++) {
            if (annotation.noteheads[i] !== '#000000')
              colour = annotation.noteheads[i];
          }
          if (colour) {
            ctx.fillStyle = colour;
            const path = new Path2D(entry.path);
            let ctm = entry.ctm;
            ctx.transform(ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f);
            ctx.fill(path);
            ctm = ctm.inverse();
            ctx.transform(ctm.a, ctm.b, ctm.c, ctm.d, ctm.e, ctm.f);
          }
        }

        // Text
        ctx.fillStyle = '#0000FF';
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 1;
        ctx.font = 'bold 8px Roboto, Noto Sans, sans-serif';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        for (const [entry, annotation] of iterEntries()) {
          if (annotation.rightText) {
            const OFFSET = 1;
            const args = [
              annotation.rightText,
              entry.bBox.x + entry.bBox.width + OFFSET,
              entry.bBox.y + 0.5 * entry.bBox.height];
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
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.lineWidth = 2;
        const RADIUS = 4;
        for (const key in this.annotations.structures) {
          if (!this.annotations.structures.hasOwnProperty(key)) continue;
          const [u, v] = key.split(':');
          const entry = this.annotations.structures[key];
          const upos = this.findNoteLocation(u), vpos = this.findNoteLocation(v);
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
      }
      if (pageIndex < this.pages.length)
        this.ensureLoaded(pageIndex);

      this.drawTimeTotal += Date.now() - start;
      this.drawTimeCount += 1;
    },

    resize() {
      if (!this.$refs.canvas) return; // Not sure why this happens
      console.info('Resizing');
      let ratio = window.devicePixelRatio;
      // This avoids ugly aliasing
      if (ratio === 1) ratio = 2;
      this.ratio = ratio;
      this.width = this.canvas.width = this.$refs.canvas.clientWidth * ratio;
      this.height = this.canvas.height = this.$refs.canvas.clientHeight * ratio;
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
      if (!this.pages || !this.bitmaps[0]) return;
      // Convert to canvas units
      const canvasX = e.offsetX * this.ratio, canvasY = e.offsetY * this.ratio;

      const match = this.visiblePages.find(p => p.pageX <= canvasX);
      if (!match) return;

      const pageIndex = match.pageIndex;

      const x = (canvasX - match.pageX) / this.realScale, y = (canvasY - match.pageY) / this.realScale;

      const noteMap = this.noteMaps[pageIndex];
      if (!noteMap) return;
      const matches = [];
      for (const key in noteMap) {
        if (!this.noteMaps[pageIndex].hasOwnProperty(key)) continue;
        const bBox = this.noteMaps[pageIndex][key].bBox;
        // console.log(bBox);
        if (bBox.x <= x && x <= bBox.x + bBox.width && bBox.y <= y && y <= bBox.y + bBox.height)
          matches.push(key);
      }
      if (matches.length) {
        this.$emit('select', matches);
      }
    },

    findNoteLocation(key) {
      for (const {pageX, pageY, pageIndex} of this.visiblePages) {
        const entry = this.noteMaps[pageIndex][key];
        if (entry) {
          return {
            x: pageX + (entry.bBox.x + 0.5 * entry.bBox.width) * this.realScale,
            y: pageY + (entry.bBox.y + 0.5 * entry.bBox.height) * this.realScale
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
      this.draw();
    },
  },

  mounted() {
    this.ctx = this.$refs.canvas.getContext('2d');
    this.ctx.imageSmoothingQuality = 'high';
    this.canvas = this.$refs.canvas;

    this.throttledResize = throttle(this.resize.bind(this));
    this.throttledDraw = throttle(this.draw.bind(this));

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

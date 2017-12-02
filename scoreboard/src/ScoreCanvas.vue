<template>
  <canvas ref="canvas" @mousewheel="onMouseWheel"></canvas>
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
  props: ['apiPrefix', 'pages', 'noteMaps', 'annotations', 'pageOffset'],
  data: () => ({
    canvas: null,
    ctx: null,
    bitmaps: [],
    pageLoadings: [],
    ratio: null,
    width: null,
    height: null,
    scale: 'fit',
    pageMargin: 32,
  }),

  computed: {
    realScale() {
      if (this.scale === 'fit') {
        if (!this.bitmaps[0]) return 1;
        const bitmap = this.bitmaps[0];
        const effectiveHeight = this.height - this.pageMargin * this.ratio * 2;
        return Math.min(this.width / bitmap.width, effectiveHeight / bitmap.height);
      }
      return this.scale;
    },
  },

  methods: {
    async loadImage(pageIndex) {
      try {
        console.info('Loading', this.pages[pageIndex]);
        this.pageLoadings[pageIndex] = true;
        const res = await fetch(this.apiPrefix + this.pages[pageIndex]);
        if (!res.ok) throw new Error('Response not ok');
        const blob = await res.blob();
        const bitmap = await createImageBitmap(blob);

        this.bitmaps[pageIndex] = bitmap;

        this.draw();
      } catch (err) {
        this.pageLoadings[pageIndex] = false;
        throw err;
      }
    },

    ensureLoaded(pageIndex) {
      if (!this.pageLoadings[pageIndex])
        this.loadImage(pageIndex);
    },

    draw() {
      this.ctx.setTransform(1, 0, 0, 1, 0, 0);
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      if (!this.pages) return;
      if (!this.bitmaps[0]) {
        this.ensureLoaded(0);
        return;
      }

      const scaledMargin = this.pageMargin * this.ratio;
      const pageWidth = this.bitmaps[0].width;
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

        // Draw page
        this.ctx.setTransform(1, 0, 0, 1, x * this.realScale, scaledMargin);
        this.ctx.drawImage(
          bitmap, 0, 0, bitmap.width * this.realScale, bitmap.height * this.realScale);

        // Annotations
        for (const colour in this.noteMaps[pageIndex]) {
          if (!this.noteMaps[pageIndex].hasOwnProperty(colour)) continue;
          const entry = this.noteMaps[pageIndex][colour];
          const annotation = this.annotations[colour];
          if (!annotation) continue;
          if (annotation.notehead1) {
            this.ctx.fillStyle = annotation.notehead1;
            for (const rect of entry.rects) {
              this.ctx.fillRect(...rect.map(x => x * this.realScale));
            }
          }
        }
      }
      if (pageIndex < this.pages.length)
        this.ensureLoaded(pageIndex);
    },

    resize() {
      console.info('Resizing');
      let ratio = window.devicePixelRatio;
      // This avoids ugly aliasing
      if (ratio === 1) ratio = 2;
      this.ratio = ratio;
      this.width = this.canvas.width = this.$refs.canvas.clientWidth * ratio;
      this.height = this.canvas.height = this.$refs.canvas.clientHeight * ratio;
      this.draw();
    },

    onMouseWheel(e) {
      e.preventDefault();
      let pageOffset = this.pageOffset + (e.deltaX || e.deltaY) / 1000;
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

  },

  watch: {
    pages() {
      this.bitmaps = this.pages.map(() => null);
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

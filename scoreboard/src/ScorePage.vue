<template>
  <div class="container">
    <div class="overlay">
      <md-progress-spinner v-if="loading" md-mode="indeterminate" :md-diameter="20"
        :md-stroke="2" class="md-accent"></md-progress-spinner>
    </div>
    <score-canvas :api-prefix="apiPrefix" :pages="pages"
      :annotations="annotations" :page-offset="pageOffset"
      @update:page-offset="x => $emit('update:page-offset', x)"></score-canvas>
  </div>
</template>

<script>
import { fetchJSON } from './common';
export default {
  name: 'ScorePage',
  props: {
    apiPrefix: String,
    score: {type: Object, required: true},
    notehead1: Object,
    pageOffset: Number,
  },
  data: () => ({
    loading: 0,
    pages: null,
    featureData: null,
  }),

  computed: {
    annotations() {
      if (!this.featureData) return null;
      const result = {};
      for (const key in this.featureData) {
        if (!this.featureData.hasOwnProperty(key)) continue;
        const data = this.featureData[key];
        // TODO: Data type aware
        result[key] = {
          notehead1: this.notehead1 && data[this.notehead1.name] ? '#3333FF' : '#000000'
        };
      }
      return result;
    },
  },

  methods: {
    async load() {
      try {
        this.loading += 1;
        const [{pages}, featureData] = await Promise.all([
          fetchJSON(this.apiPrefix + this.score.xml + '/index'),
          fetchJSON(this.apiPrefix + this.score.featureData)
        ]);
        this.pages = pages;
        this.$emit('update:page-count', this.pages.length);
        this.featureData = featureData;
      } finally {
        this.loading -= 1;
      }
    },
  },

  mounted() {
    this.load();
  },
};
</script>

<style lang="scss" scoped>
  .container {
    position: relative;
    width: 100%; height: 100%;
  }
  .overlay {
    position: absolute;
    top: 32px; left: 32px;
  }
  .score-canvas {
    width: 100%; height: 100%;
  }
</style>

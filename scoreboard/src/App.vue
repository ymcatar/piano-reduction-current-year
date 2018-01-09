<template>
  <div class="vertical-layout">
    <md-toolbar class="md-primary">
      <span class="md-title">Scoreboard</span>
      <md-menu class="run-select">
        <md-button md-menu-trigger @click="onMenuActivate">
          <template v-if="selectedRun">
            {{formatTimestamp(selectedRun.timestamp)}} ({{selectedRun.name}})
          </template>
          <template v-else>
            No run selected
          </template>
        </md-button>

        <md-menu-content>
          <md-menu-item v-for="run of runs" :key="run.name"
              @click="selectedRunName = run.name">
            <span
                :class="{'run-select-label': true, active: run.name === selectedRunName}">
              {{formatTimestamp(run.timestamp)}} ({{run.name}})
            </span>
          </md-menu-item>
        </md-menu-content>
      </md-menu>
    </md-toolbar>

    <!-- Forces recreation when run changes -->
    <run v-for="run of [selectedRun]" v-if="run" :key="run.name" :run="run"></run>
  </div>
</template>

<script>
import { apiRoot } from './config';
import { fetchJSON } from './common';
export default {
  name: 'app',
  data: () => ({
    menuOpen: true,
    loading: true,
    runs: [],
    selectedRunName: null,
  }),

  computed: {
    selectedRun() {
      return this.selectedRunName ? this.runs.find(r => r.name === this.selectedRunName) : null;
    },
  },

  mounted() {
    this.load();
  },

  methods: {
    async load() {
      console.log('Loading runs');
      const {runs} = await fetchJSON(apiRoot + 'log/index.json');
      this.runs = runs;
      if (!this.selectedRunName && this.runs.length)
        this.selectedRunName = this.runs[0].name;
    },

    formatTimestamp(timestamp) {
      return new Date(timestamp * 1000).toString().substr(4, 20);
    },

    onSelectRun(run) {
      this.selectedRunName = run.name;
    },

    onMenuActivate() {
      this.load();
    },
  },
};
</script>

<style lang="scss" scoped>
.vertical-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.run-select {
  margin-left: 32px;
}
</style>
<style lang="scss">
.run-select-label.active {
  color: #448aff !important;
}
</style>

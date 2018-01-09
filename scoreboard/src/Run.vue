<template>
  <div class="horizontal-layout">
    <md-card class="drawer">
      <md-list class="md-dense">
        <md-subheader>Scores</md-subheader>
        <md-list-item v-for="score of run.scores" :key="score.name">
          <md-radio v-model="selectedScoreName" :value="score.name"
            class="md-primary "/>
          <span class="md-list-item-text">
            {{score.name}}
          </span>
        </md-list-item>

        <md-subheader>Controls</md-subheader>
        <md-list-item>
          <div class="page-slider">
            <span>Page</span>
            <input type="range" min="0" :max="pageCount-0.5" step="0.1" v-model.number="pageOffset">
            <span class="page-disp">{{Math.round(pageOffset*10)/10}}</span>
          </div>
        </md-list-item>

        <md-subheader>Features</md-subheader>
        <template v-for="i of [0, 1]">
          <md-list-item :key="i">
            <md-field>
              <label :for="'notehead' + i">Notehead {{i}}</label>
              <md-select v-model="noteheads[i]" :id="'notehead' + i">
                <md-option key="null" value="none"></md-option>
                <md-option v-for="feature of run.features" :key="feature.name"
                    :value="feature.name">
                  {{feature.name}}
                </md-option>
              </md-select>
            </md-field>
          </md-list-item>

          <md-list-item>
            <div class="help">
              <feature-legend v-if="noteheads[i]"
                :feature="getFeature(noteheads[i], 'notehead' + i)"></feature-legend>
            </div>
          </md-list-item>
        </template>

      </md-list>
    </md-card>

    <main>
      <!-- Forces recreation when score changes -->
      <score-page v-for="score of [selectedScore]" v-if="selectedScore"
        :key="score.name" :api-prefix="apiPrefix" :score="selectedScore"
        :noteheads="noteheads.map((n, i) => getFeature(n, 'notehead'+i))"
        :page-offset="pageOffset"
        @update:page-offset="x => pageOffset = x"
        @update:page-count="x => pageCount = x"></score-page>
    </main>
  </div>
</template>

<script>
import { apiRoot } from './config';
export default {
  name: 'Run',
  props: {
    run: {type: Object, required: true},
  },
  data: () => ({
    selectedScoreName: null,
    noteheads: [null, null],
    pageOffset: 0.0,
    pageCount: 100,
    defaultColours: {
      notehead0: '#FF0000',
      notehead1: '#33FF33',
    },
  }),

  computed: {
    selectedScore() {
      return this.run.scores.find(s => s.name === this.selectedScoreName);
    },

    apiPrefix() {
      return apiRoot + 'log/' + this.run.name + '/';
    }
  },

  methods: {
    getFeature(name, target) {
      let feature = this.run.features.find(f => f.name === name);
      if (feature && target) {
        feature = Object.assign({}, feature);
        feature.colour = this.defaultColours[target];
      }
      return feature;
    },
  },

  mounted() {
    if (this.run.scores.length)
      this.selectedScoreName = this.run.scores[0].name;
  },
};
</script>

<style lang="scss" scoped>
.horizontal-layout {
  flex: 1;
  display: flex;
    .drawer { width: 240px; }
    main { flex: 1; overflow-x: scroll; }
}

.help {
  overflow-y: auto;
  height: 160px;
  white-space: normal;
}

.page-slider {
  display: flex; align-items: center;
  width: 100%;
  input { flex: 1; margin-left: 8px; margin-right: 8px; }
  .page-disp { width: 32px; }
}
</style>

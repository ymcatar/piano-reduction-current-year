<template>
  <div class="horizontal-layout">
    <md-card class="drawer">
      <md-list class="md-dense" v-if="!selectedNotes.length">
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
            <input type="range" min="0" :max="pages ? pages.length-0.5 : 0"
              step="0.1" v-model.number="pageOffset">
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

      <md-list class="md-dense inspector" v-else>
        <md-subheader>
          <h2 style="flex: 1">
            Inspect note
          </h2>
          <md-button class="md-icon-button" @click="selectedNotes = []">
            <md-icon>close</md-icon>
          </md-button>
        </md-subheader>
        <div v-for="id of selectedNotes" :key="id">
          <md-subheader>Note {{id}}</md-subheader>
          <md-list-item>
            <div>
              <p v-for="v, k in featureData[id]">{{k}}: {{v}}</p>
            </div>
          </md-list-item>
        </div>
      </md-list>
    </md-card>

    <main>
      <!-- Forces recreation when score changes -->
      <div v-for="score of [selectedScore]" v-if="selectedScore" class="container"
          :key="score.name">
        <div class="overlay">
          <md-progress-spinner v-if="loading" md-mode="indeterminate" :md-diameter="20"
            :md-stroke="2" class="md-accent"></md-progress-spinner>
        </div>
        <score-canvas :api-prefix="apiPrefix" :pages="pages"
          :annotations="annotations" @select="x => selectedNotes = x"
          :page-offset.sync="pageOffset"
          @update:page-offset="x => pageOffset = x"></score-canvas>
      </div>
    </main>
  </div>
</template>

<script>
import { apiRoot } from './config';
import { fetchJSON } from './common';
export default {
  name: 'Run',
  props: {
    run: {type: Object, required: true},
  },
  data: () => ({
    selectedScoreName: null,

    loading: 0,
    pages: null,
    featureData: null,

    noteheads: [null, null],

    pageOffset: 0.0,
    pageCount: 100,
    selectedNotes: [],

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
    },

    annotations() {
      if (!this.featureData) return null;

      const noteheads = this.noteheads.map((key, i) => this.getFeature(key, 'notehead' + i));

      const selectedData = this.featureData[this.selectedNotes[0]] || {};
      const selectedPitch = selectedData._pitch;
      const selectedPitchClass = selectedData._pitch_class;

      const result = {};
      for (const key in this.featureData) {
        if (!this.featureData.hasOwnProperty(key)) continue;
        const data = this.featureData[key];
        // TODO: Data type aware
        const props = {
          noteheads: noteheads.map(() => '#000000'),
          circle: null,
        };
        for (let i = 0; i < noteheads.length; i++) {
          const nh = noteheads[i];
          if (nh) {
            const value = data[nh.name];
            if (nh.dtype === 'categorical') {
              const labelEntry = nh.legend[value];
              props.noteheads[i] = labelEntry ? labelEntry[0] : nh.default;
            } else {
              props.noteheads[i] = value ? nh.colour : '#000000';
            }
          }
        }
        if (this.selectedNotes.includes(key)) {
          props.circle = '#FF0000';
        } else if (data._pitch === selectedPitch) {
          props.circle = '#FFBB66';
        } else if (data._pitch_class === selectedPitchClass) {
          props.circle = '#FFFF99';
        }
        result[key] = props;
      }
      return result;
    },
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

    async loadFeatureData() {
      const score = this.selectedScore;
      this.pages = null;
      this.featureData = null;
      if (!score) return;
      try {
        this.loading += 1;
        const [{pages}, featureData] = await Promise.all([
          fetchJSON(this.apiPrefix + score.xml.substr(0, score.xml.length - 4) + '-index.json'),
          fetchJSON(this.apiPrefix + score.featureData)
        ]);
        if (score !== this.selectedScore) return;
        this.pages = pages;
        this.featureData = featureData;
      } finally {
        this.loading -= 1;
      }
    },
  },

  watch: {
    selectedScoreName() {
      this.loadFeatureData();
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
  .drawer { width: 300px; height: calc(100vh - 64px); overflow-y: auto; }
  main { flex: 1; }
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

.inspector .md-subheader { margin-top: 16px !important; }

.inspector p {
  margin-top: 3px; margin-bottom: 3px;
}
</style>

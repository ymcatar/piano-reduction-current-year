<template>
  <div class="horizontal-layout">
    <md-card class="drawer">
      <md-list class="md-dense" v-if="!selectedNotes.length">
        <md-subheader>Scores</md-subheader>
        <md-list-item v-for="score of run.scores" :key="score.name">
          <md-radio v-model="selectedScoreName" :value="score.name"
            class="md-primary "/>
          <span class="md-list-item-text">
            {{score.title ? `${score.title} (${score.name})` : score.name}}
          </span>
        </md-list-item>

        <md-subheader>
          <span>Information</span>
          <span style="flex: 1"></span>
          <md-button class="md-icon-button" @click="showInfo = !showInfo">
            <md-icon>arrow_drop_{{showInfo ? 'up' : 'down'}}</md-icon>
          </md-button>
        </md-subheader>
        <md-list-item v-if="showInfo && selectedScore && selectedScore.help">
          <div class="info-help">{{selectedScore.help}}</div>
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
        <template v-for="key of annotationKeys">
          <md-list-item :key="key">
            <md-field>
              <label :for="key">{{key}}</label>
              <md-select v-model="annotationMap[key]" :id="key" md-dense>
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
              <feature-legend v-if="annotationMap[key]"
                :type="annotationTypes[key]" :feature="getFeature(key)">
              </feature-legend>
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
import { interpolateRgbBasis } from 'd3-interpolate';
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

    annotationKeys: ['notehead0', 'notehead1', 'rightText'],
    annotationTypes: {
      notehead0: 'colour',
      notehead1: 'colour',
      rightText: 'text',
    },
    annotationMap: {},

    pageOffset: 0.0,
    pageCount: 100,
    selectedNotes: [],

    showInfo: false,

    defaults: (o => {
      for (const k in o)
        if (o.hasOwnProperty(k))
          o[k].colourSpace = interpolateRgbBasis(o[k].colourBasis);
      return o;
    })({
      notehead0: {
        colour: '#FF0000',
        colourBasis: ['#000000', '#FF0000', '#FF9900', '#FFFF00'],
      },
      notehead1: {
        colour: '#33FF33',
        colourBasis: ['#000000', '#00FF00', '#00FFFF', '#0000FF'],
      },
    }),
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

      const noteheads = [];
      for (let i = 0; this.annotationKeys.includes('notehead' + i); i++) {
        noteheads.push(this.getFeature('notehead' + i));
      }

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
            } else if (nh.dtype === 'float') {
              // Interpolation
              const t = (value - nh.range[0]) / (nh.range[1] - nh.range[0]);
              props.noteheads[i] = nh.colourSpace(t).toString();
            } else {
              props.noteheads[i] = value ? nh.colour : '#000000';
            }
          }
        }
        const rightText = this.getFeature('rightText');
        if (rightText) {
          const value = data[this.annotationMap['rightText']];
          if (typeof value === 'boolean') {
            props.rightText = value ? '+' : '';
          } else if (typeof value === 'number') {
            const rounded = Math.round(value * 100) / 100;
            props.rightText = String(rounded);
          } else if (typeof value !== 'undefined' && value !== null) {
            props.rightText = String(value);
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
    getFeature(annotation) {
      const name = this.annotationMap[annotation];
      let feature = this.run.features.find(f => f.name === name);
      if (feature && annotation) {
        feature = Object.assign({}, this.defaults[annotation], feature);
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

.info-help {
  overflow-y: auto;
  white-space: pre-line;
}

.help {
  overflow-y: auto;
  height: 110px;
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

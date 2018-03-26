<template>
  <div class="horizontal-layout">
    <md-card class="drawer">
      <md-list class="md-dense" :style="{display: !selectedNotes.length ? 'block' : 'none'}">
        <md-subheader>Scores</md-subheader>
        <md-list-item v-for="score of run.scores" :key="score.name">
          <md-radio v-model="selectedScoreName" :value="score.name"
            class="md-primary "/>
          <span class="md-list-item-text">
            {{score.title ? `${score.title} (${score.name})` : score.name}}
          </span>
          <form method="get" :action="apiPrefix + score.xml">
            <md-button class="md-icon-button md-dense" type="submit" @click.stop="true">
              <md-icon>file_download</md-icon>
            </md-button>
          </form>
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
          <md-button class="md-icon-button md-dense" @click="onChangePage(-1)">
            <md-icon>keyboard_arrow_left</md-icon>
          </md-button>
          <md-button class="md-icon-button md-dense" @click="onChangePage(1)">
            <md-icon>keyboard_arrow_right</md-icon>
          </md-button>
        </md-list-item>

        <md-list-item>
          <md-field>
            <label for="playback">Playback</label>
            <md-select v-model="selectedPlaybackScoreName" id="playback" md-dense>
              <md-option key="null" value="none"></md-option>
                <md-option v-for="score of run.scores" :key="score.name" :value="score.name">
                  {{score.title ? `${score.title} (${score.name})` : score.name}}
                </md-option>
            </md-select>
          </md-field>
        </md-list-item>

        <audio v-if="selectedPlaybackScore" controls>
          <source :src="apiPrefix + dropExt(selectedPlaybackScore.xml) + '.mp3'"
              type="audio/mpeg">
        </audio>

        <md-subheader>
          <span style="flex: 1">Features</span>
          <md-menu>
            <md-button md-menu-trigger class="md-icon-button">
              <md-icon>more_horiz</md-icon>
            </md-button>

            <md-menu-content>
              <md-menu-item v-for="config, name in savedConfigs" :key="name"
                  @click="onLoadConfig(config)">
                  {{name}}
              </md-menu-item>
              <md-menu-item @click="onSaveConfig()">
                  <strong>Save Current</strong>
              </md-menu-item>
            </md-menu-content>
          </md-menu>
        </md-subheader>
        <template v-for="key of annotationKeys">
          <md-list-item :key="key">
            <md-field class="feature-field">
              <label :for="key">{{key}}</label>
              <md-select v-model="annotationMap[key]" :id="key" md-dense>
                <md-option key="null" value="none"></md-option>
                <md-optgroup v-for="(features, group) in featureGroups"
                  :key="group" :label="group || '(No group)'">
                  <md-option v-for="feature of features" :key="feature.name"
                      :value="feature.name">
                    {{feature.name}}
                  </md-option>
                </md-optgroup>
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

        <md-list-item>
          <md-field class="feature-field">
            <label for="ray">ray</label>
            <md-select v-model="annotationMap.ray" id="ray" md-dense>
              <md-option key="null" value="none"></md-option>
                <md-optgroup v-for="(features, group) in structureFeatureGroups"
                  :key="group" :label="group || '(No group)'">
                  <md-option v-for="feature of features" :key="feature.name"
                      :value="feature.name">
                    {{feature.name}}
                  </md-option>
                </md-optgroup>
            </md-select>
          </md-field>
        </md-list-item>

        <md-list-item>
          <div class="help">
            <feature-legend v-if="annotationMap.ray"
              :type="annotationTypes.ray" :feature="getFeature('ray', true)">
            </feature-legend>
          </div>
        </md-list-item>

      </md-list>

      <md-list class="md-dense inspector" v-if="selectedNotes.length">
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
              <p v-for="v, k in featureData.notes[id]">{{k}}: {{v}}</p>
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
    selectedPlaybackScoreName: null,

    loading: 0,
    pages: null,
    featureData: null,

    annotationKeys: ['notehead0', 'notehead1', 'rightText', 'bottomText'],
    annotationTypes: {
      notehead0: 'colour',
      notehead1: 'colour',
      rightText: 'text',
      bottomText: 'text',
      ray: 'colour',
    },
    annotationMap: {},

    pageOffset: 0.0,
    pageCount: 100,
    selectedNotes: [],

    showInfo: false,

    defaults: (o => {
      for (const k in o)
        if (o.hasOwnProperty(k) && o[k].colourBasis)
          o[k].colourSpace = interpolateRgbBasis(o[k].colourBasis);
      return o;
    })({
      notehead0: {
        colour: '#FF9900',
        colourBasis: ['#000000', '#FF0000', '#FF9900', '#FFFF00'],
      },
      notehead1: {
        colour: '#33FF33',
        colourBasis: ['#000000', '#00FF00', '#00FFFF', '#0000FF'],
      },
      rightText: {
        colour: '#9900FF',
      },
      bottomText: {
        colour: '#009900',
      },
      ray: {
        colour: '#33DDDD',
      },
    }),

    savedConfigs: {},
  }),

  computed: {
    selectedScore() {
      return this.run.scores.find(s => s.name === this.selectedScoreName);
    },

    selectedPlaybackScore() {
      return this.run.scores.find(s => s.name === this.selectedPlaybackScoreName);
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

      const selectedData = this.featureData.notes[this.selectedNotes[0]] || {};
      const selectedPitch = selectedData._pitch;
      const selectedPitchClass = selectedData._pitch_class;

      const notes = {};
      for (const key in this.featureData.notes) {
        if (!this.featureData.notes.hasOwnProperty(key)) continue;
        const data = this.featureData.notes[key];
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
        for (const key of ['rightText', 'bottomText']) {
          const feature = this.getFeature(key);
          if (!feature) continue;
          const value = data[this.annotationMap[key]];
          let formatted;
          if (typeof value === 'boolean') {
            formatted = value ? '+' : '';
          } else if (typeof value === 'number') {
            const rounded = Math.round(value * 100) / 100;
            formatted = String(rounded);
          } else if (typeof value !== 'undefined' && value !== null) {
            formatted = String(value);
          }
          if (typeof formatted !== 'undefined') {
            props[key] = {text: formatted, colour: feature.colour};
          }
        }
        if (this.selectedNotes.includes(key)) {
          props.circle = '#FF0000';
        } else if (data._pitch === selectedPitch) {
          props.circle = '#FFBB66';
        } else if (data._pitch_class === selectedPitchClass) {
          props.circle = '#FFFF99';
        }
        notes[key] = props;
      }

      const structures = {};
      const ray = this.getFeature('ray', /*structured*/ true);
      if (ray) {
        const data = this.featureData.structures[ray.name];
        for (const key in data) {
          if (!data.hasOwnProperty(key)) continue;
          structures[key] = {colour: ray.colour, text: data[key], directed: ray.directed};
        }
      }
      return {notes, structures};
    },

    featureGroups() {
      const ret = {};
      for (const feature of this.run.features) {
        const group = feature.group || '';
        ret[group] = ret[group] || [];
        ret[group].push(feature);
      }
      return ret;
    },

    structureFeatureGroups() {
      const ret = {};
      for (const feature of this.run.structureFeatures) {
        const group = feature.group || '';
        ret[group] = ret[group] || [];
        ret[group].push(feature);
      }
      return ret;
    },
  },

  methods: {
    getFeature(annotation, structured = false) {
      const name = this.annotationMap[annotation];
      let feature = (structured ? this.run.structureFeatures : this.run.features)
          .find(f => f.name === name);
      if (feature && annotation) {
        feature = Object.assign({}, this.defaults[annotation], feature);
      }
      return feature;
    },

    dropExt(path) {
      return path.substr(0, path.lastIndexOf('.'));
    },

    async loadFeatureData() {
      const score = this.selectedScore;
      this.pages = null;
      this.featureData = null;
      if (!score) return;
      try {
        this.loading += 1;
        const [{pages}, featureData] = await Promise.all([
          fetchJSON(this.apiPrefix + this.dropExt(score.xml) + '-index.json'),
          fetchJSON(this.apiPrefix + score.featureData)
        ]);
        if (score !== this.selectedScore) return;
        this.pages = pages;
        this.featureData = featureData;
        // Backward compatibility
        if (!this.featureData.notes) {
          this.featureData = {
            notes: this.featureData,
            structures: {}
          };
        }
      } finally {
        this.loading -= 1;
      }
    },

    onChangePage(offset) {
      const maxPage = (this.pages ? this.pages.length : 0) - 1;
      this.pageOffset = Math.max(0, Math.min(maxPage, this.pageOffset + offset));
    },

    onLoadConfig(config) {
      if (config.annotationMap)
        this.annotationMap = Object.assign({}, this.annotationMap, config.annotationMap);
    },

    onSaveConfig() {
      const name = window.prompt('Name of config:');
      if (!name) return;
      this.savedConfigs[name] = {
        annotationMap: Object.assign({}, this.annotationMap),
      };
      this.savedConfigs = Object.assign({}, this.savedConfigs);
      localStorage['scoreboard:savedConfigs'] = JSON.stringify(this.savedConfigs, null, 4);
    }
  },

  watch: {
    selectedScoreName() {
      this.loadFeatureData();
    },
  },

  mounted() {
    if (this.run.scores.length === 1)
      this.selectedScoreName = this.run.scores[0].name;

    try {
      this.savedConfigs = JSON.parse(localStorage['scoreboard:savedConfigs']);
    } catch (err) {
      this.savedConfigs = {};
    }
  },
};
</script>

<style lang="scss" scoped>
.horizontal-layout {
  min-height: 0;
  flex: 1;
  display: flex;
  .drawer { width: 300px; height: calc(100vh - 64px); overflow-y: auto; }
  main { flex: 1; }
}

.info-help {
  overflow: auto;
  white-space: pre;
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
  .page-disp { width: 20px; }
}

audio {
  height: 32px;
  background-color: white;
}

.feature-field {
  margin-bottom: 0;
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

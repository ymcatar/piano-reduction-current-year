import Vue from 'vue';
import VueMaterial from 'vue-material';
import 'vue-material/dist/vue-material.min.css';
import 'vue-material/dist/theme/default.css';

Vue.use(VueMaterial);

import Run from './Run.vue';
Vue.component('run', Run);
import ScorePage from './ScorePage.vue';
Vue.component('score-page', ScorePage);
import ScoreCanvas from './ScoreCanvas.vue';
Vue.component('score-canvas', ScoreCanvas);

import App from './App.vue';
new Vue({
  el: '#app',
  render: h => h(App)
});

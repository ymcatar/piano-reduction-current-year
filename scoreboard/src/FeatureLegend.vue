<template>
  <div v-if="feature">
    <p>{{feature.help}}</p>
    <p>Type: {{feature.dtype}}</p>
    <template v-if="feature.dtype === 'categorical'">
      <div v-for="(stuff, value) in feature.legend" class="label">
        <div v-if="type === 'colour'" class="colour-box" :style="{backgroundColor: stuff[0]}"></div>
        <div v-else class="text-box">{{value}}</div>
        <div>{{stuff[1]}}</div>
      </div>
    </template>
    <template v-else-if="feature.dtype === 'float'">
      <div class="label">
        <div v-if="type === 'colour'" class="colour-bar"
            :style="{background: `linear-gradient(to right, ${feature.colourBasis.join(', ')})`}"></div>
        <div v-else class="text-box">+</div>
        <div>Value [{{feature.range[0]}}, {{feature.range[1]}}]</div>
      </div>
    </template>
    <template v-else>
      <div class="label">
        <div v-if="type === 'colour'" class="colour-box" :style="{backgroundColor: feature.colour}"></div>
        <div v-else class="text-box">+</div>
        <div>True label</div>
      </div>
    </template>
  </div>
</template>

<script>
export default {
  name: 'FeatureLegend',
  props: ['feature', 'type'],
  data: () => ({
  }),
};
</script>

<style lang="scss" scoped>
  .label {
    display: flex;
    align-items: center;
  }
  .colour-box, .colour-bar {
    width: 15px; height: 10px;
    border: 1px solid black;
    margin-top: 4px; margin-bottom: 4px;
    margin-right: 4px;
    flex-shrink: 0;
  }
  .colour-bar {
    width: 60px;
  }
  .text-box {
    margin-right: 4px;
    min-width: 60px;

    font-size: 0.8em;
    color: #ff0000;
  }
</style>

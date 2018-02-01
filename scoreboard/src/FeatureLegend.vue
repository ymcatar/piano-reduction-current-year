<template>
  <div v-if="feature">
    <p>{{feature.help}}</p>
    <p>Type: {{feature.dtype}}</p>
    <template v-if="feature.dtype === 'categorical'">
      <div v-for="(stuff, value) in feature.legend" class="label">
        <div class="label-box" :style="{backgroundColor: stuff[0]}"></div>
        <div>{{stuff[1]}}</div>
      </div>
    </template>
    <template v-else>
      <div class="label">
        <div class="label-box" :style="{backgroundColor: feature.colour}"></div>
        <div>True label</div>
      </div>
    </template>
  </div>
</template>

<script>
export default {
  name: 'FeatureLegend',
  props: ['feature'],
  data: () => ({
  }),
};
</script>

<style lang="scss" scoped>
  .label {
    display: flex;
    align-items: center;
  }
  .label-box {
    width: 15px;
    height: 10px;
    border: 1px solid black;
    margin-top: 4px; margin-bottom: 4px;
    margin-right: 4px;
    flex-shrink: 0;
  }
</style>

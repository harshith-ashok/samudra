import { createRouter, createWebHistory } from 'vue-router';
import MapView from '../views/MapView.vue';
import DatasetsView from '../views/DatasetsView.vue';

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'map', component: MapView },
    { path: '/datasets', name: 'datasets', component: DatasetsView },
  ],
});

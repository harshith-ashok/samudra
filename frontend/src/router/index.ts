import { createRouter, createWebHistory } from "vue-router";
import MapView from "../views/MapView.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [{ path: "/", name: "map", component: MapView }],
});

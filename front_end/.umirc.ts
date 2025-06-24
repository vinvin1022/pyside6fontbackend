import { defineConfig } from "umi";

export default defineConfig({
   headScripts: [
    { src: '/qwebchannel.js', defer: true },
  ],
  routes: [
    { path: "/", component: "index" },
    { path: "/docs", component: "docs" },
    { path: "/message", component: "message" },
  ],
  npmClient: 'yarn',
});

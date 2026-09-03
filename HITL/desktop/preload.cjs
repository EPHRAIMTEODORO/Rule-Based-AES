const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("hitlDesktop", {
  platform: process.platform,
});

const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  appName: "AI Examiner"
});
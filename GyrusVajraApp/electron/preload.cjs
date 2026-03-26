const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    trimVideo: (args) => ipcRenderer.invoke('trim-video', args),
});

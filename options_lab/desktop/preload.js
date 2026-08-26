const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('desktopAPI', {
  platform: process.platform,
  isDesktop: true,
  version: '2.0.0'
});

contextBridge.exposeInMainWorld('electronAPI', {
  openSaxoOauth: (authUrl) => ipcRenderer.invoke('open-saxo-oauth', authUrl),
  onSaxoAuthSuccess: (callback) => {
    ipcRenderer.on('saxo-auth-success', () => callback());
  }
});

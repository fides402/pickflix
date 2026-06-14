/* Kiwi Fast Nav – Service Worker */

chrome.runtime.onInstalled.addListener(({ reason }) => {
  if (reason === 'install') {
    chrome.storage.sync.set({
      skipAds: true,
      removeBloat: true,
      touchGestures: true,
      autoDismissConsent: true,
      autoTheater: false,
      skipCountdown: true,
      hideShortsRedirect: true,
      seekSeconds: 10,
    });
  }
});

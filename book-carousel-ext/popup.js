const OPENROUTER_KEY   = 'INSERISCI_QUI_LA_TUA_CHIAVE_OPENROUTER'; // sk-or-v1-...
const OPENROUTER_MODEL = 'meta-llama/llama-3.1-8b-instruct:free';

let pdfBase64 = null;
let pdfName   = null;

const dropZone       = document.getElementById('drop-zone');
const pdfInput       = document.getElementById('pdf-input');
const fileNameEl     = document.getElementById('file-name');
const chatgptStatus  = document.getElementById('chatgpt-status');
const statusTextEl   = document.getElementById('status-text');
const chapterInfoEl  = document.getElementById('chapter-info');
const capNumEl       = document.getElementById('cap-num');
const capSubEl       = document.getElementById('cap-sub');
const statusLog      = document.getElementById('status-log');
const btnGenerate    = document.getElementById('btn-generate');
const btnOpenChatgpt = document.getElementById('btn-open-chatgpt');
const btnReset       = document.getElementById('btn-reset');
const carouselsList  = document.getElementById('carousels-list');
const clLabel        = document.getElementById('cl-label');

// ── Init ──
async function init() {
  const state = await getState();
  renderState(state);
  pollChatGPTTab();
  setInterval(pollChatGPTTab, 3000);
}

async function getState() {
  return new Promise(resolve => {
    chrome.storage.local.get(['chapter', 'carousels', 'chatGptTabId', 'pdfName'], data => {
      resolve({
        chapter:      data.chapter    || 1,
        carousels:    data.carousels  || [],
        chatGptTabId: data.chatGptTabId || null,
        pdfName:      data.pdfName    || null,
      });
    });
  });
}

function renderState(state) {
  capNumEl.textContent = state.chapter;
  capSubEl.textContent = state.chapter === 1
    ? 'Pronto per generare il primo carosello'
    : `${state.carousels.length} carosell${state.carousels.length === 1 ? 'o' : 'i'} già generati`;

  if (state.chapter > 1) {
    chapterInfoEl.style.display = 'block';
    btnReset.style.display = 'block';
  }
  if (state.pdfName) {
    fileNameEl.textContent = state.pdfName;
    dropZone.classList.add('has-file');
    pdfName = state.pdfName;
  }
  renderCarousels(state.carousels);
  updateGenerateBtn(state);
}

function updateGenerateBtn(state) {
  const hasPdf = !!pdfBase64 || (state.chapter > 1);
  btnGenerate.textContent = `✨ Genera Capitolo ${state.chapter}`;
  btnGenerate.disabled = !hasPdf;
}

function renderCarousels(carousels) {
  if (!carousels.length) return;
  clLabel.style.display = 'block';
  carouselsList.style.display = 'block';
  carouselsList.innerHTML = '';
  carousels.forEach((c, i) => {
    const el = document.createElement('div');
    el.className = 'cl-item';
    el.innerHTML = `
      <div>
        <div class="cl-title">Capitolo ${i + 1}</div>
        <div class="cl-slides">${c.slides.length} slide</div>
      </div>
      <div class="cl-arrow">›</div>`;
    el.onclick = () => openCarousel(c);
    carouselsList.appendChild(el);
  });
}

// ── ChatGPT tab detection ──
async function pollChatGPTTab() {
  const tabs = await chrome.tabs.query({ url: ['https://chat.openai.com/*', 'https://chatgpt.com/*'] });
  if (tabs.length) {
    chatgptStatus.classList.add('connected');
    statusTextEl.textContent = 'ChatGPT connesso ✓';
    chrome.storage.local.set({ chatGptTabId: tabs[0].id });
  } else {
    chatgptStatus.classList.remove('connected');
    statusTextEl.textContent = 'Apri ChatGPT in una scheda...';
  }
}

// ── PDF upload ──
dropZone.addEventListener('click', () => pdfInput.click());
pdfInput.addEventListener('change', e => handleFile(e.target.files[0]));
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
  if (!file || file.type !== 'application/pdf') {
    setStatus('Seleziona un file PDF valido.', 'error');
    return;
  }
  pdfName = file.name;
  const reader = new FileReader();
  reader.onload = async e => {
    pdfBase64 = e.target.result.split(',')[1];
    fileNameEl.textContent = file.name;
    dropZone.classList.add('has-file');
    chrome.storage.local.set({ pdfName: file.name });
    const state = await getState();
    updateGenerateBtn(state);
    setStatus('PDF pronto.', 'success');
  };
  reader.readAsDataURL(file);
}

// ── Buttons ──
btnOpenChatgpt.addEventListener('click', () => chrome.tabs.create({ url: 'https://chatgpt.com/' }));

btnReset.addEventListener('click', async () => {
  if (!confirm('Ricominciare da capo? I caroselli salvati verranno eliminati.')) return;
  await chrome.storage.local.clear();
  pdfBase64 = null; pdfName = null;
  fileNameEl.textContent = '';
  dropZone.classList.remove('has-file');
  carouselsList.innerHTML = '';
  clLabel.style.display = 'none';
  carouselsList.style.display = 'none';
  btnReset.style.display = 'none';
  chapterInfoEl.style.display = 'none';
  btnGenerate.disabled = true;
  btnGenerate.textContent = '✨ Genera Capitolo 1';
  capNumEl.textContent = '1';
  setStatus('', '');
});

btnGenerate.addEventListener('click', handleGenerate);

async function handleGenerate() {
  const state = await getState();
  const chapter = state.chapter;

  const tabs = await chrome.tabs.query({ url: ['https://chat.openai.com/*', 'https://chatgpt.com/*'] });
  if (!tabs.length) {
    setStatus('Apri ChatGPT prima di procedere.', 'error');
    return;
  }
  const tab = tabs[0];

  btnGenerate.disabled = true;
  setStatus('<span class="spinner"></span>Invio a ChatGPT...', 'active');

  // Clear previous response state from storage before starting
  await new Promise(r => chrome.storage.local.remove('_responseState', r));

  try {
    let response;
    if (chapter === 1 && pdfBase64) {
      response = await sendToContentScript(tab.id, {
        action: 'uploadPdfAndPrompt',
        pdfBase64, pdfName,
        prompt: buildPrompt(chapter),
      });
    } else {
      response = await sendToContentScript(tab.id, {
        action: 'sendPrompt',
        prompt: buildPrompt(chapter),
      });
    }
    if (!response.success) throw new Error(response.error || 'Errore ChatGPT');

    setStatus('<span class="spinner"></span>ChatGPT sta scrivendo...', 'active');

    // Poll chrome.storage instead of messaging the tab — survives tab switches
    const rawText = await waitForChatGPTResponse();
    setStatus('<span class="spinner"></span>Strutturando le slide con AI...', 'active');

    const rawSlides = await parseSlidesWithAI(rawText, chapter);
    const slides = rawSlides.filter(s => s.title?.trim() && s.content?.trim());
    if (!slides.length) throw new Error('Nessuna slide estratta. Assicurati che ChatGPT abbia usato il formato [SLIDE N]...[/SLIDE N].');

    const newCarousel = { chapter, slides, rawText, createdAt: Date.now() };
    const carousels = [...state.carousels, newCarousel];
    await chrome.storage.local.set({ carousels, chapter: chapter + 1 });

    setStatus(`✓ ${slides.length} slide generate per il Capitolo ${chapter}`, 'success');
    chapterInfoEl.style.display = 'block';
    btnReset.style.display = 'block';
    capNumEl.textContent = chapter + 1;
    capSubEl.textContent = `${carousels.length} carosello${carousels.length > 1 ? 'i' : ''} generato${carousels.length > 1 ? 'i' : ''}`;
    btnGenerate.textContent = `✨ Genera Capitolo ${chapter + 1}`;
    btnGenerate.disabled = false;
    renderCarousels(carousels);
    openCarousel(newCarousel);

  } catch (err) {
    setStatus('Errore: ' + err.message, 'error');
    btnGenerate.disabled = false;
  }
}

// ── Polling from chrome.storage — no tab-message required ──
function waitForChatGPTResponse() {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Timeout: ChatGPT non ha risposto in 3 minuti')), 180000);

    function poll() {
      chrome.storage.local.get('_responseState', data => {
        const r = data._responseState;
        if (!r) { setTimeout(poll, 1500); return; }

        if (r.done && r.text) {
          clearTimeout(timeout);
          resolve(r.text);
          return;
        }
        if (r.generating) {
          setStatus(`<span class="spinner"></span>ChatGPT sta scrivendo… (${r.textLength || 0} car.)`, 'active');
        } else if (r.textLength > 0) {
          setStatus(`<span class="spinner"></span>Verifica stabilità… (${r.textLength} car.)`, 'active');
        } else {
          setStatus('<span class="spinner"></span>In attesa della risposta di ChatGPT…', 'active');
        }
        setTimeout(poll, 1500);
      });
    }
    // First poll after 8s to give ChatGPT time to start
    setTimeout(poll, 8000);
  });
}

function buildPrompt(chapter) {
  if (chapter === 1) {
    return `Hai ricevuto questo libro in PDF. Analizza il CAPITOLO 1 e crea un carosello di 8-10 slide altamente engaging e divulgative, pensate per i social media.

Ogni slide deve:
- Avere un titolo breve e impattante (max 8 parole)
- Contenere 2-4 punti chiave o un paragrafo breve (max 60 parole)
- Usare un linguaggio accessibile, diretto, coinvolgente
- Includere una emoji rilevante

Usa ESATTAMENTE questo formato per ogni slide:

[SLIDE 1]
EMOJI: 🔥
TITOLO: Titolo della slide
CONTENUTO: Testo della slide con i punti chiave del capitolo
[/SLIDE 1]

[SLIDE 2]
...

Assicurati che il carosello racconti una storia progressiva e che ogni slide sia un hook per la successiva.`;
  }
  return `Perfetto! Ora fai lo stesso per il CAPITOLO ${chapter}: crea un carosello di 8-10 slide engaging con lo stesso formato:

[SLIDE 1]
EMOJI: 🔥
TITOLO: Titolo della slide
CONTENUTO: Testo della slide
[/SLIDE 1]

[SLIDE 2]
...

Usa lo stesso stile divulgativo e coinvolgente del carosello precedente.`;
}

function sendToContentScript(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, response => {
      if (chrome.runtime.lastError) {
        chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] }, () => {
          setTimeout(() => {
            chrome.tabs.sendMessage(tabId, message, response2 => {
              if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
              else resolve(response2);
            });
          }, 600);
        });
      } else {
        resolve(response);
      }
    });
  });
}

async function parseSlidesWithAI(rawText, chapter) {
  const slides = parseSlides(rawText);
  if (slides.length >= 3) return slides;

  try {
    const res = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENROUTER_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://book-carousel-ext',
        'X-Title': 'Book Carousel',
      },
      body: JSON.stringify({
        model: OPENROUTER_MODEL,
        messages: [{
          role: 'user',
          content: `Estrai le slide dal seguente testo e restituisci SOLO un array JSON valido nel formato:
[{"emoji":"🔥","title":"Titolo","content":"Testo della slide"}]

Testo:
${rawText.slice(0, 6000)}

Rispondi SOLO con il JSON, niente altro.`,
        }],
        max_tokens: 2000,
        temperature: 0.3,
      }),
    });
    const data = await res.json();
    const text = data.choices?.[0]?.message?.content || '';
    const jsonMatch = text.match(/\[[\s\S]*\]/);
    if (jsonMatch) return JSON.parse(jsonMatch[0]);
  } catch (e) {
    console.error('OpenRouter parse error:', e);
  }
  return slides;
}

function parseSlides(text) {
  const slides = [];
  const re = /\[SLIDE\s*(\d+)\]([\s\S]*?)\[\/SLIDE\s*\1\]/gi;
  let m;
  while ((m = re.exec(text)) !== null) {
    const block   = m[2];
    const emoji   = (block.match(/EMOJI:\s*(.+)/i)          || [])[1]?.trim() || '📖';
    const title   = (block.match(/TITOLO:\s*(.+)/i)         || [])[1]?.trim() || '';
    const content = (block.match(/CONTENUTO:\s*([\s\S]+)/i) || [])[1]?.trim() || '';
    if (title) slides.push({ emoji, title, content });
  }
  return slides;
}

function openCarousel(carousel) {
  const url = chrome.runtime.getURL('carousel.html');
  chrome.storage.local.set({ activeCarousel: carousel }, () => {
    chrome.tabs.create({ url });
  });
}

function setStatus(html, type) {
  statusLog.innerHTML = html;
  statusLog.className = type ? `status-log ${type}` : 'status-log';
  statusLog.style.color = type === 'error' ? '#f87171' : type === 'success' ? '#4ade80' : type === 'active' ? '#a78bfa' : '#555';
}

init();

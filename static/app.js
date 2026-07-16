(function () {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
  }
  const $ = (id) => document.getElementById(id);
  const dropzone = $("dropzone");
  const fileInput = $("file-input");
  const fileList = $("file-list");
  const apiKey = $("api-key");
  const consent = $("consent");
  const generateBtn = $("generate-btn");
  const excelBtn = $("excel-btn");
  const clearBtn = $("clear-btn");
  const statusCard = $("status-card");
  const statusLog = $("status-log");
  const resultCard = $("result-card");
  const resultMd = $("result-md");
  let files = [];
  let lastResult = null;

  apiKey.value = sessionStorage.getItem("psychoPortraitApiKey") || "";
  apiKey.addEventListener("input", () => {
    sessionStorage.setItem("psychoPortraitApiKey", apiKey.value);
    refreshButtons();
  });
  consent.addEventListener("change", refreshButtons);

  ["dragenter", "dragover"].forEach((name) => dropzone.addEventListener(name, (event) => {
    event.preventDefault(); dropzone.classList.add("dragover");
  }));
  ["dragleave", "drop"].forEach((name) => dropzone.addEventListener(name, (event) => {
    event.preventDefault(); dropzone.classList.remove("dragover");
  }));
  dropzone.addEventListener("drop", (event) => addFiles(event.dataTransfer.files));
  dropzone.addEventListener("click", (event) => {
    if (!event.target.closest("button")) fileInput.click();
  });
  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") fileInput.click();
  });
  $("browse-btn").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => addFiles(fileInput.files));
  clearBtn.addEventListener("click", () => { files = []; fileInput.value = ""; renderFiles(); });

  function addFiles(next) {
    const accepted = Array.from(next).filter((file) => /\.(pptx|pdf)$/i.test(file.name));
    const existing = new Set(files.map((file) => `${file.name}:${file.size}:${file.lastModified}`));
    accepted.forEach((file) => {
      const key = `${file.name}:${file.size}:${file.lastModified}`;
      if (!existing.has(key)) { files.push(file); existing.add(key); }
    });
    renderFiles();
  }

  function renderFiles() {
    fileList.innerHTML = "";
    files.forEach((file, index) => {
      const li = document.createElement("li");
      li.textContent = `${index + 1}. ${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} МБ`;
      fileList.appendChild(li);
    });
    fileList.classList.toggle("hidden", files.length === 0);
    refreshButtons();
  }

  function refreshButtons() {
    const ready = consent.checked && (apiKey.value.trim().length > 0 || location.hostname === "127.0.0.1" || location.hostname === "localhost");
    clearBtn.disabled = files.length === 0;
    generateBtn.disabled = !(ready && files.length === 1);
    excelBtn.disabled = !(ready && files.length > 0);
  }

  function headers() {
    const value = apiKey.value.trim();
    return value ? { "X-API-Key": value } : {};
  }

  function log(message, kind = "info") {
    const line = document.createElement("div");
    line.className = `log-line ${kind}`;
    line.textContent = message;
    statusLog.appendChild(line);
  }

  async function errorMessage(response) {
    try {
      const body = await response.json();
      if (typeof body.detail === "string") return body.detail;
      if (body.detail && body.detail.message) return body.detail.message;
      return body.error || `Ошибка ${response.status}`;
    } catch (_) { return `Ошибка ${response.status}`; }
  }

  generateBtn.addEventListener("click", async () => {
    statusCard.classList.remove("hidden");
    resultCard.classList.add("hidden");
    statusLog.innerHTML = "";
    log("Извлекаю показатели и проверяю достоверность...");
    setBusy(true);
    const form = new FormData();
    form.append("file", files[0]);
    try {
      const response = await fetch("/api/generate", { method: "POST", headers: headers(), body: form });
      if (!response.ok) throw new Error(await errorMessage(response));
      const data = await response.json();
      lastResult = data;
      resultMd.textContent = data.characteristics_markdown;
      resultCard.classList.remove("hidden");
      log(`Готово. Модель: ${data.model}`, "ok");
      (data.report?.quality_warnings || []).forEach((item) => log(item, "warn"));
    } catch (error) { log(error.message, "err"); }
    finally { setBusy(false); }
  });

  excelBtn.addEventListener("click", async () => {
    statusCard.classList.remove("hidden");
    resultCard.classList.add("hidden");
    statusLog.innerHTML = "";
    log(`Формирую ${files.length} характеристик и книгу Excel...`);
    setBusy(true);
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    try {
      const response = await fetch("/api/batch/generate-xlsx", { method: "POST", headers: headers(), body: form });
      if (!response.ok) throw new Error(await errorMessage(response));
      const blob = await response.blob();
      downloadBlob(blob, "psychological_characteristics.xlsx");
      log("Excel сформирован и скачан", "ok");
    } catch (error) { log(error.message, "err"); }
    finally { setBusy(false); }
  });

  function setBusy(busy) {
    generateBtn.textContent = busy ? "Обработка..." : "Характеристика одного";
    excelBtn.textContent = busy ? "Обработка..." : "Сформировать Excel";
    generateBtn.disabled = busy;
    excelBtn.disabled = busy;
    clearBtn.disabled = busy;
    if (!busy) refreshButtons();
  }

  function downloadBlob(blob, name) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = name; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  $("copy-btn").addEventListener("click", async () => {
    if (lastResult) await navigator.clipboard.writeText(lastResult.characteristics_markdown);
  });
  $("download-btn").addEventListener("click", () => {
    if (!lastResult) return;
    const blob = new Blob([lastResult.characteristics_markdown], { type: "text/markdown;charset=utf-8" });
    downloadBlob(blob, "psychological_characteristic.md");
  });
  renderFiles();
})();

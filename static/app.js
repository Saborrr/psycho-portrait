// Psycho Portrait — frontend
(function () {
  const $ = (id) => document.getElementById(id);
  const dropzone = $("dropzone");
  const fileInput = $("file-input");
  const browseBtn = $("browse-btn");
  const clearBtn = $("clear-btn");
  const fileName = $("file-name");
  const dzFile = $("dz-file");
  const dzContent = dropzone.querySelector(".dz-content");
  const generateBtn = $("generate-btn");
  const briefMode = $("brief-mode");
  const statusCard = $("status-card");
  const statusLog = $("status-log");
  const resultCard = $("result-card");
  const resultMd = $("result-md");
  const copyBtn = $("copy-btn");
  const downloadBtn = $("download-btn");
  const downloadPdfBtn = $("download-pdf-btn");
  const debugCard = $("debug-card");
  const debugProfile = $("debug-profile");

  let currentFile = null;
  let lastResult = null;

  // === Drag & drop ===
  ["dragenter", "dragover"].forEach((ev) => {
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });
  ["dragleave", "drop"].forEach((ev) => {
    dropzone.addEventListener(ev, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });
  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length) setFile(files[0]);
  });
  dropzone.addEventListener("click", (e) => {
    if (e.target.closest("button") || e.target.closest(".dz-file")) return;
    fileInput.click();
  });
  browseBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    fileInput.click();
  });
  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length) setFile(e.target.files[0]);
  });
  clearBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    setFile(null);
  });

  function setFile(file) {
    currentFile = file;
    if (file) {
      fileName.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} КБ)`;
      dzContent.classList.add("hidden");
      dzFile.classList.remove("hidden");
      generateBtn.disabled = false;
    } else {
      fileInput.value = "";
      dzContent.classList.remove("hidden");
      dzFile.classList.add("hidden");
      generateBtn.disabled = true;
    }
  }

  // === Status log ===
  function log(msg, kind = "info") {
    const line = document.createElement("div");
    line.className = `log-line ${kind}`;
    const ts = new Date().toLocaleTimeString();
    line.textContent = `[${ts}] ${msg}`;
    statusLog.appendChild(line);
    statusLog.scrollTop = statusLog.scrollHeight;
  }

  // === Generate ===
  generateBtn.addEventListener("click", async () => {
    if (!currentFile) return;
    statusCard.classList.remove("hidden");
    resultCard.classList.add("hidden");
    debugCard.classList.add("hidden");
    statusLog.innerHTML = "";
    generateBtn.disabled = true;
    generateBtn.textContent = "Генерирую…";

    log(`📄 Файл: ${currentFile.name} (${(currentFile.size / 1024).toFixed(1)} КБ)`);
    log("🔍 Парсим PPTX…", "info");

    const fd = new FormData();
    fd.append("file", currentFile);
    fd.append("style", briefMode.checked ? "brief" : "default");

    try {
      const t0 = Date.now();
      const resp = await fetch("/api/generate", { method: "POST", body: fd });

      if (!resp.ok) {
        const errText = await resp.text();
        let errJson;
        try { errJson = JSON.parse(errText); } catch { errJson = { error: errText }; }
        log(`❌ Ошибка ${resp.status}: ${errJson.error || resp.statusText}`, "err");
        if (errJson.details) {
          errJson.details.forEach((d) => log(`  • ${d}`, "warn"));
        }
        if (errJson.raw_text_preview) {
          log("📄 Превью текста из PPTX (первые 2кб):", "info");
          log(errJson.raw_text_preview, "info");
        }
        return;
      }

      const data = await resp.json();
      const dt = ((Date.now() - t0) / 1000).toFixed(1);
      log(`✅ Готово за ${dt}с`, "ok");
      log(`🤖 Модель: ${data.model}`, "info");
      if (data.profile?.notes?.length) {
        data.profile.notes.forEach((n) => log(`  • ${n}`, "warn"));
      }

      lastResult = data;
      resultMd.textContent = data.characteristics_markdown;
      resultCard.classList.remove("hidden");
      debugProfile.textContent = JSON.stringify(data.profile, null, 2);
      debugCard.classList.remove("hidden");
    } catch (e) {
      log(`❌ Сетевая ошибка: ${e.message}`, "err");
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = "Сгенерировать характеристику";
    }
  });

  // === Actions ===
  copyBtn.addEventListener("click", async () => {
    if (!lastResult) return;
    try {
      await navigator.clipboard.writeText(lastResult.characteristics_markdown);
      copyBtn.textContent = "✅ Скопировано!";
      setTimeout(() => (copyBtn.textContent = "📋 Скопировать"), 1500);
    } catch (e) {
      alert("Не удалось скопировать: " + e.message);
    }
  });

  downloadBtn.addEventListener("click", () => {
    if (!lastResult) return;
    const md = lastResult.characteristics_markdown;
    const fname = (lastResult.profile?.employee?.full_name || "characteristic").replace(/\s+/g, "_") + ".md";
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fname;
    a.click();
    URL.revokeObjectURL(url);
  });

  // PDF — простой, через window.print(); для продвинутого — будем делать через бэкенд
  downloadPdfBtn.addEventListener("click", () => {
    if (!lastResult) return;
    const md = lastResult.characteristics_markdown;
    // Простая конвертация markdown → HTML → печать в PDF
    const html = `<!doctype html><html><head><meta charset="utf-8"><title>Характеристика</title>
      <style>body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;line-height:1.7;color:#222}
      h1,h2,h3{margin-top:1.5rem}h1{border-bottom:2px solid #444;padding-bottom:.3rem}
      h2{color:#333;border-bottom:1px solid #ccc;padding-bottom:.2rem}
      table{border-collapse:collapse;margin:1rem 0}td,th{border:1px solid #999;padding:.4rem .7rem}
      </style></head><body><pre style="white-space:pre-wrap;font-family:inherit">${md.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]))}</pre>
      <script>window.onload=()=>setTimeout(()=>window.print(),300);<\/script>
      </body></html>`;
    const w = window.open("", "_blank");
    if (!w) { alert("Разреши всплывающие окна для PDF"); return; }
    w.document.write(html);
    w.document.close();
  });
})();

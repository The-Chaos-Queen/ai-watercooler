document.addEventListener('DOMContentLoaded', async () => {
    const status = document.getElementById('status');
    const exportBtn = document.getElementById('exportBtn');
    const title = document.getElementById('title');

    // Platform mapping for UI and Filenames
    const PLATFORMS = {
        'claude.ai': 'Claude',
        'kimi.moonshot.cn': 'Kimi',
        'kimi.com': 'Kimi',
        'chat.mistral.ai': 'Mistral',
        'grok.com': 'Grok',
        'gemini.google.com': 'Gemini',
        'chat.deepseek.com': 'DeepSeek',
        'lmsys.org': 'LMArena',
        'arena.ai': 'LMArena'
    };

    // 1. Get Active Tab to set UI
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Detect Platform
    let platformName = 'AI';
    if (tab && tab.url) {
        // Find matching key
        const match = Object.keys(PLATFORMS).find(key => tab.url.includes(key));
        if (match) {
            platformName = PLATFORMS[match];
        }
    }

    // Update UI
    exportBtn.innerText = `Export ${platformName} Chat`;
    // title.innerText = `${platformName} Exporter`; // Optional: keep title generic or specific

    exportBtn.addEventListener('click', async () => {
        status.innerText = "Connecting...";

        // Inject content script if needed
        try {
            await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                files: ['content.js']
            });
        } catch (e) {
            console.log("Script injection skipped/failed (likely already there):", e);
        }

        // Send message
        chrome.tabs.sendMessage(tab.id, { action: "get_chat" }, (response) => {
            if (chrome.runtime.lastError) {
                status.innerText = "Error: " + chrome.runtime.lastError.message;
                return;
            }

            if (response && response.status === "success") {
                const markdown = response.data;
                if (markdown.includes("> **Error**")) {
                    status.innerText = "Warning: No messages found.";
                } else {
                    status.innerText = `Success! (${markdown.length} bytes)`;
                }

                // Filename Generation
                const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
                const filename = `${platformName.toLowerCase()}_chat_${timestamp}.md`;

                // Download
                const blob = new Blob([markdown], { type: "text/markdown" });
                const url = URL.createObjectURL(blob);

                chrome.downloads.download({
                    url: url,
                    filename: filename,
                    saveAs: true
                });
            } else {
                status.innerText = "Failed: " + (response ? response.message : "No response");
            }
        });
    });
});

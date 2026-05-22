/**
 * DeepSeek Batch Chat Exporter — paste into Chrome DevTools Console (F12)
 *
 * Navigates to each chat via sidebar clicks, scrolls to collect all messages
 * including thinking blocks, and downloads each as a markdown file.
 *
 * INSTRUCTIONS:
 * 1. Open DeepSeek chat in Chrome
 * 2. Open sidebar and scroll to bottom so all chats are visible
 * 3. Press F12 → Console tab
 * 4. Paste this entire script and press Enter
 * 5. Wait — it will download each chat as a .md file automatically
 *
 * Author: Warden, 2026-03-28
 */

(async function deepseekBatchExport() {
  const DELAY = (ms) => new Promise(r => setTimeout(r, ms));
  const CHAT_LOAD_WAIT = 3000;
  const SCROLL_STEP = 800;
  const SCROLL_WAIT = 150;

  // Collect all chat links from the sidebar
  const links = document.querySelectorAll('a[href*="/a/chat/s/"]');
  if (links.length === 0) {
    console.error('No chat links found. Open the sidebar and scroll to the bottom first.');
    return;
  }
  console.log(`Found ${links.length} chats. Starting export...`);

  const results = [];

  for (let i = 0; i < links.length; i++) {
    const link = links[i];
    const chatTitle = link.textContent.trim();
    console.log(`[${i + 1}/${links.length}] Navigating to: ${chatTitle}`);

    // Click the sidebar link (SPA navigation, no page reload)
    link.click();
    await DELAY(CHAT_LOAD_WAIT);

    // Collect messages by scrolling through the virtual list
    const vlist = document.querySelector('.ds-virtual-list');
    if (!vlist) {
      console.warn(`  No virtual list found for "${chatTitle}", skipping`);
      results.push({ title: chatTitle, error: 'no vlist' });
      continue;
    }

    const collected = new Map();
    const order = [];

    const collectVisible = () => {
      document.querySelectorAll('.ds-message').forEach(m => {
        const isUser = m.classList.length > 2;
        const key = (isUser ? 'U' : 'A') + ':' + m.textContent.substring(0, 50).replace(/\s+/g, ' ');

        if (!collected.has(key)) {
          const entry = {
            role: isUser ? 'Human' : 'DeepSeek',
            thinking: null,
            content: ''
          };

          if (isUser) {
            const inner = m.querySelector('div');
            entry.content = inner ? inner.textContent.trim() : m.textContent.trim();
          } else {
            Array.from(m.children).forEach(child => {
              if (child.querySelector('.ds-think-content')) {
                entry.thinking = child.querySelector('.ds-think-content').textContent.trim();
              } else if (child.classList.contains('ds-markdown')) {
                entry.content = child.innerText.trim();
              }
            });
          }

          collected.set(key, entry);
          order.push(key);
        }
      });
    };

    // Scroll from top to bottom
    vlist.scrollTop = 0;
    await DELAY(400);
    collectVisible();

    for (let pos = SCROLL_STEP; pos <= vlist.scrollHeight + SCROLL_STEP; pos += SCROLL_STEP) {
      vlist.scrollTop = pos;
      await DELAY(SCROLL_WAIT);
      collectVisible();
    }

    // Build markdown
    const pageTitle = document.title.replace(' - DeepSeek', '').trim();
    let md = `# ${pageTitle}\n\n`;
    md += `**Source:** DeepSeek\n`;
    md += `**URL:** ${window.location.href}\n`;
    md += `**Exported:** ${new Date().toISOString()}\n\n---\n\n`;

    order.forEach(key => {
      const msg = collected.get(key);
      md += `## ${msg.role}\n\n`;
      if (msg.thinking) {
        md += `> **Thinking:**\n>\n`;
        msg.thinking.split('\n').forEach(line => {
          md += `> ${line}\n`;
        });
        md += '\n';
      }
      md += msg.content + '\n\n---\n\n';
    });

    // Generate safe filename
    const safeTitle = pageTitle.replace(/[<>:"/\\|?*]/g, '').replace(/\s+/g, '_').substring(0, 80);
    const filename = `DeepSeek_${safeTitle}.md`;

    // Trigger download
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    console.log(`  ✓ ${filename} (${order.length} messages, ${md.length} chars)`);
    results.push({ title: chatTitle, filename, messages: order.length, chars: md.length });

    // Brief pause between downloads so Chrome doesn't throttle
    await DELAY(500);
  }

  console.log('\n=== EXPORT COMPLETE ===');
  console.log(`Exported ${results.length} chats:`);
  results.forEach((r, i) => {
    if (r.error) {
      console.log(`  ${i + 1}. ✗ ${r.title} (${r.error})`);
    } else {
      console.log(`  ${i + 1}. ✓ ${r.filename} (${r.messages} msgs, ${r.chars} chars)`);
    }
  });

  // Also log results as JSON for easy processing
  console.log('\nJSON results:', JSON.stringify(results, null, 2));
})();

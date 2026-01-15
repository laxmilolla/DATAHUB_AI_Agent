#!/usr/bin/env node
/**
 * MCP Server for Playwright Browser Automation
 * Simple stdio-based MCP server (no HTTP bridge needed)
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { chromium } from 'playwright';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Browser state
let browser = null;
let page = null;
let context = null;

// Screenshot counter
let screenshotCounter = 0;

// Initialize MCP server
const server = new Server(
  {
    name: 'playwright-browser',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

/**
 * Initialize browser if not already running
 */
async function ensureBrowser() {
  if (!browser) {
    browser = await chromium.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-blink-features=AutomationControlled'
      ]
    });
    
    context = await browser.newContext({
      viewport: { width: 1280, height: 720 },
      userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    });
    
    page = await context.newPage();
    console.error('Browser initialized'); // stderr for logging
  }
}

/**
 * List available tools
 */
server.setRequestHandler('tools/list', async () => {
  return {
    tools: [
      {
        name: 'browser_navigate',
        description: 'Navigate browser to a URL',
        inputSchema: {
          type: 'object',
          properties: {
            url: {
              type: 'string',
              description: 'URL to navigate to (must include protocol)'
            }
          },
          required: ['url']
        }
      },
      {
        name: 'browser_snapshot',
        description: 'Get current page HTML/DOM',
        inputSchema: {
          type: 'object',
          properties: {}
        }
      },
      {
        name: 'browser_click',
        description: 'Click an element on the page',
        inputSchema: {
          type: 'object',
          properties: {
            selector: {
              type: 'string',
              description: 'CSS selector or text selector'
            }
          },
          required: ['selector']
        }
      },
      {
        name: 'browser_fill',
        description: 'Fill an input field with text',
        inputSchema: {
          type: 'object',
          properties: {
            selector: {
              type: 'string',
              description: 'CSS selector for the input field'
            },
            text: {
              type: 'string',
              description: 'Text to fill'
            }
          },
          required: ['selector', 'text']
        }
      },
      {
        name: 'browser_screenshot',
        description: 'Take a screenshot of the current page',
        inputSchema: {
          type: 'object',
          properties: {
            name: {
              type: 'string',
              description: 'Filename for the screenshot'
            }
          },
          required: ['name']
        }
      },
      {
        name: 'browser_evaluate',
        description: 'Execute JavaScript on the page',
        inputSchema: {
          type: 'object',
          properties: {
            code: {
              type: 'string',
              description: 'JavaScript code to execute'
            }
          },
          required: ['code']
        }
      }
    ]
  };
});

/**
 * Handle tool calls
 */
server.setRequestHandler('tools/call', async (request) => {
  const { name, arguments: args } = request.params;
  
  try {
    await ensureBrowser();
    
    switch (name) {
      case 'browser_navigate': {
        const { url } = args;
        console.error(`Navigating to: ${url}`);
        
        await page.goto(url, { 
          waitUntil: 'networkidle',
          timeout: 30000 
        });
        
        return {
          content: [{
            type: 'text',
            text: `Successfully navigated to ${url}`
          }]
        };
      }
      
      case 'browser_snapshot': {
        console.error('Getting page snapshot');
        const html = await page.content();
        
        // Truncate if too large (keep first 50KB for LLM context)
        const truncated = html.length > 50000 
          ? html.substring(0, 50000) + '\n\n[... HTML truncated for brevity ...]'
          : html;
        
        return {
          content: [{
            type: 'text',
            text: truncated
          }]
        };
      }
      
      case 'browser_click': {
        const { selector } = args;
        console.error(`Clicking: ${selector}`);
        
        // Wait for element to be visible
        await page.waitForSelector(selector, { 
          state: 'visible',
          timeout: 10000 
        });
        
        await page.click(selector);
        
        // Wait for potential navigation
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        
        return {
          content: [{
            type: 'text',
            text: `Successfully clicked ${selector}`
          }]
        };
      }
      
      case 'browser_fill': {
        const { selector, text } = args;
        console.error(`Filling ${selector} with: ${text}`);
        
        await page.waitForSelector(selector, { 
          state: 'visible',
          timeout: 10000 
        });
        
        await page.fill(selector, text);
        
        return {
          content: [{
            type: 'text',
            text: `Successfully filled ${selector} with text`
          }]
        };
      }
      
      case 'browser_screenshot': {
        const { name: filename } = args;
        screenshotCounter++;
        
        const screenshotPath = join(__dirname, '..', 'storage', 'screenshots', `${screenshotCounter}_${filename}.png`);
        console.error(`Taking screenshot: ${screenshotPath}`);
        
        await page.screenshot({ 
          path: screenshotPath,
          fullPage: false 
        });
        
        return {
          content: [{
            type: 'text',
            text: `Screenshot saved to ${screenshotPath}`
          }]
        };
      }
      
      case 'browser_evaluate': {
        const { code } = args;
        console.error(`Evaluating JavaScript`);
        
        const result = await page.evaluate(code);
        
        return {
          content: [{
            type: 'text',
            text: JSON.stringify(result, null, 2)
          }]
        };
      }
      
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
    
  } catch (error) {
    console.error(`Error in ${name}:`, error.message);
    return {
      content: [{
        type: 'text',
        text: `Error: ${error.message}`
      }],
      isError: true
    };
  }
});

/**
 * Cleanup on exit
 */
process.on('SIGINT', async () => {
  console.error('Shutting down...');
  if (browser) {
    await browser.close();
  }
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.error('Shutting down...');
  if (browser) {
    await browser.close();
  }
  process.exit(0);
});

/**
 * Start server
 */
async function main() {
  console.error('Starting MCP Playwright server...');
  
  const transport = new StdioServerTransport();
  await server.connect(transport);
  
  console.error('MCP server ready');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});



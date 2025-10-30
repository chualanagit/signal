# Streaming Reply API

## Overview

The Intent Finder now supports **Server-Sent Events (SSE)** for real-time response generation, providing a better UX by showing text as it's generated.

## Endpoints

### 1. `/reply/stream` - Streaming Response (NEW) ⚡

Returns Server-Sent Events (SSE) stream with response chunks as they're generated.

**Method:** `POST`

**Request Body:**
```json
{
  "topic": "CRM for small business",
  "post": {
    "source": "reddit",
    "title": "Looking for CRM recommendations",
    "url": "https://reddit.com/r/smallbusiness/example",
    "snippet": "Need help choosing a CRM for our team"
  }
}
```

**Response:** `text/event-stream`

**SSE Format:**
```
data: Hi there! For
data:  a 10
data: -person team
data: , I recommend
...
data: [DONE]
```

**JavaScript Client Example:**
```javascript
const response = await fetch('/reply/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, post })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let fullText = '';

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
        if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
                console.log('Complete:', fullText);
                return;
            }
            fullText += data;
            console.log('Chunk:', data);
        }
    }
}
```

---

### 2. `/reply` - Non-Streaming Response (Original) 📦

Returns complete response in single JSON payload. Use for simple clients or batch processing.

**Method:** `POST`

**Request Body:** Same as streaming endpoint

**Response:**
```json
{
  "response": "Hi there! For a 10-person team, I recommend..."
}
```

---

## When to Use Each

| Use Case | Endpoint | Why |
|----------|----------|-----|
| **Web UI** | `/reply/stream` | Real-time feedback, better UX |
| **Mobile Apps** | `/reply/stream` | Progressive display |
| **Batch Processing** | `/reply` | Simpler, wait for complete response |
| **Simple Clients** | `/reply` | No SSE parsing needed |
| **API Integrations** | `/reply` | Standard REST response |

---

## Features

✅ **Automatic Fallback** - Frontend tries streaming first, falls back to regular endpoint if streaming fails

✅ **Connection Pooling** - Both endpoints use shared `httpx.AsyncClient` for efficiency

✅ **Error Handling** - Streams `[ERROR]` messages if generation fails

✅ **Production Ready** - Includes headers to disable nginx buffering

---

## Performance Benefits

**Streaming (`/reply/stream`):**
- ⚡ **Perceived Speed**: Users see text immediately (Time to First Byte)
- 🎯 **Better UX**: Progress indication, feels faster
- 🔄 **Incremental Rendering**: Can start reading before completion

**Non-Streaming (`/reply`):**
- 📦 **Simpler**: Single request/response
- 🛠️ **Easier**: No SSE parsing needed
- 📊 **Batch-Friendly**: Better for analytics/logging

---

## Testing

**Test Streaming:**
```bash
curl -N -X POST http://localhost:8000/reply/stream \
  -H "Content-Type: application/json" \
  -d '{"topic":"test","post":{"source":"reddit","title":"test","url":"http://example.com","snippet":"test"}}'
```

**Test Non-Streaming:**
```bash
curl -X POST http://localhost:8000/reply \
  -H "Content-Type: application/json" \
  -d '{"topic":"test","post":{"source":"reddit","title":"test","url":"http://example.com","snippet":"test"}}'
```


# Astra Playground

A web-based UI for interacting with Astra agents, tools, and workflows.

## Features

- **Agent Chat**: Real-time chat with agents using SSE streaming
- **Tools Browser**: View and test available tools
- **Workflows Viewer**: Visualize and monitor workflows
- **Dark Theme**: Modern dark UI matching Mastra Studio design

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The dev server runs on `http://localhost:3000` and proxies API requests to `http://localhost:8000`.

## Building for Production

```bash
# Build and copy to runtime
npm run build:copy
```

This builds the app and copies it to `packages/runtime/src/astra/server/playground-dist/`.

## Integration with Runtime

When the Astra Runtime server starts, it automatically serves the playground at the root URL if the built files are present.

```
🚀 Astra Runtime starting...
📊 API available at: http://localhost:8000/api
👨‍💻 Playground available at: http://localhost:8000/
```

## Stack

- React 19
- TypeScript
- Vite
- Tailwind CSS
- TanStack Query
- React Router 7

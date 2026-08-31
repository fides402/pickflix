import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

const dirname = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        reader: `${dirname}reader.html`,
        background: `${dirname}src/background.ts`,
        chatgptBridge: `${dirname}src/contentScripts/chatgptBridge.ts`,
      },
      output: {
        entryFileNames: (chunk) =>
          chunk.name === "background" || chunk.name === "chatgptBridge"
            ? "[name].js"
            : "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
});

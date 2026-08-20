import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import childProcess from "node:child_process";

const require = createRequire(import.meta.url);

globalThis.self = globalThis;

const originalExec = childProcess.exec;
const originalExecFile = childProcess.execFile;

childProcess.exec = function patchedExec(command, options, callback) {
  const cb = typeof options === "function" ? options : callback;
  if (typeof cb === "function") {
    queueMicrotask(() => cb(null, "", ""));
  }
  return { pid: process.pid, kill() {} };
};

childProcess.execFile = function patchedExecFile(file, args, options, callback) {
  const cb = typeof options === "function" ? options : callback;
  if (typeof cb === "function") {
    queueMicrotask(() => cb(null, "", ""));
  }
  return { pid: process.pid, kill() {} };
};

const esbuild = require("esbuild-wasm/lib/browser.js");
const wasmPath = require.resolve("esbuild-wasm/esbuild.wasm");
const wasmModule = new WebAssembly.Module(fs.readFileSync(wasmPath));

await esbuild.initialize({ wasmModule, worker: false });

const esbuildPath = require.resolve("esbuild");
require.cache[esbuildPath] = { id: esbuildPath, filename: esbuildPath, loaded: true, exports: esbuild };

await import(pathToFileURL(path.resolve("node_modules/vite/bin/vite.js")).href);

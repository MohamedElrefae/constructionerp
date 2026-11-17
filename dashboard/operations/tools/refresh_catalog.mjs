#!/usr/bin/env node
/** T3 protocol-2 read-only registry producer. Node >=22; no external JS packages.
 * Requires an operator-provisioned NON-MCP bearer session with orchestration:read only.
 * No credential discovery, token creation/renewal, provider refresh/probe or model execution.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";

const MAX_BYTES = 4_000_000;
const publisher = fileURLToPath(
  new URL("./publish_catalog.py", import.meta.url)
);
const READ_SCOPES = new Set([
  "orchestration:read",
  "filesystem:read",
  "diagnostics:read",
]);
export class CatalogError extends Error {}
function requireSafe(ok) {
  if (!ok) throw new CatalogError("Catalog refresh refused");
}

function privatePath(filename) {
  const absolute = path.resolve(filename);
  for (let current = absolute; ; current = path.dirname(current)) {
    try {
      requireSafe(!fs.lstatSync(current).isSymbolicLink());
    } catch (e) {
      if (e.code !== "ENOENT") throw e;
    }
    if (current === path.dirname(current)) break;
  }
  const parent = fs.statSync(path.dirname(absolute));
  requireSafe(
    parent.isDirectory() &&
      parent.uid === process.getuid() &&
      !(parent.mode & 0o077)
  );
  return absolute;
}
function readToken(filename) {
  const location = privatePath(filename);
  const fd = fs.openSync(
    location,
    fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK
  );
  try {
    const st = fs.fstatSync(fd);
    requireSafe(
      st.isFile() &&
        st.uid === process.getuid() &&
        !(st.mode & 0o077) &&
        st.nlink === 1 &&
        st.size <= 8192
    );
    const token = fs.readFileSync(fd, "utf8").trim();
    requireSafe(token.length > 0 && !/[\s\x00-\x1f\x7f]/.test(token));
    return token;
  } finally {
    fs.closeSync(fd);
  }
}
export function safeOrigin(origin) {
  const url = new URL(origin);
  requireSafe(
    !url.username &&
      !url.password &&
      !url.search &&
      !url.hash &&
      url.pathname === "/"
  );
  requireSafe(
    url.protocol === "https:" ||
      (url.protocol === "http:" &&
        ["127.0.0.1", "[::1]"].includes(url.hostname))
  );
  return url.origin;
}
async function boundedJson(response, max = MAX_BYTES) {
  requireSafe(
    response.ok &&
      response.headers.get("content-type")?.includes("application/json")
  );
  const reader = response.body.getReader();
  let bytes = 0;
  const chunks = [];
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.length;
      requireSafe(bytes <= max);
      chunks.push(value);
    }
  } finally {
    await reader.cancel();
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}
async function authJson(origin, route, token, method = "GET") {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    return await boundedJson(
      await fetch(new URL(route, origin), {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
        redirect: "error",
        signal: controller.signal,
      }),
      16384
    );
  } finally {
    clearTimeout(timer);
  }
}
async function getRegistry(origin, ticket) {
  const url = new URL("/ws", origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("orchestrationProtocol", "2");
  url.searchParams.set("wsTicket", ticket);
  return await new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    let finished = false;
    let total = 0;
    const finish = (value, failed = false) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      // Native socket errors and ticket-bearing URLs must never reach logs.
      if (failed) reject(new CatalogError("Catalog RPC failed"));
      else resolve(value);
      ws.close();
    };
    const timer = setTimeout(() => finish(null, true), 10000);
    ws.addEventListener("open", () =>
      ws.send(
        JSON.stringify({
          _tag: "Request",
          id: "1",
          tag: "server.getConfig",
          payload: {},
          headers: [],
        })
      )
    );
    ws.addEventListener("message", (event) => {
      try {
        requireSafe(typeof event.data === "string");
        total += Buffer.byteLength(event.data);
        requireSafe(total <= MAX_BYTES);
        const decoded = JSON.parse(event.data);
        for (const msg of Array.isArray(decoded) ? decoded : [decoded]) {
          if (msg._tag === "Ping") {
            ws.send(JSON.stringify({ _tag: "Pong" }));
            continue;
          }
          requireSafe(
            msg._tag === "Exit" &&
              msg.requestId === "1" &&
              msg.exit?._tag === "Success"
          );
          requireSafe(Array.isArray(msg.exit.value?.providers));
          finish(msg.exit.value);
        }
      } catch (_) {
        finish(null, true);
      }
    });
    ws.addEventListener("error", () => finish(null, true));
    ws.addEventListener("close", () => {
      if (!finished) finish(null, true);
    });
  });
}
export async function refresh({
  origin,
  tokenFile,
  output,
  python = "python3",
}) {
  origin = safeOrigin(origin);
  output = privatePath(output);
  // Validate credentials before any network I/O. Re-read every time for operator rotation.
  const token = readToken(tokenFile);
  const session = await authJson(origin, "/api/auth/session", token);
  requireSafe(
    session.authenticated === true &&
      session.sessionMethod === "bearer-access-token"
  );
  requireSafe(
    Array.isArray(session.scopes) &&
      session.scopes.includes("orchestration:read")
  );
  for (const scopes of [
    session.scopes,
    session.permissions ?? session.scopes,
  ]) {
    requireSafe(
      Array.isArray(scopes) && scopes.every((scope) => READ_SCOPES.has(scope))
    );
  }
  const issued = await authJson(
    origin,
    "/api/auth/websocket-ticket/rpc",
    token,
    "POST"
  );
  requireSafe(
    typeof issued.ticket === "string" &&
      issued.ticket.length > 0 &&
      issued.ticket.length <= 8192
  );
  requireSafe(Date.parse(issued.expiresAt) > Date.now());
  const registry = await getRegistry(origin, issued.ticket);
  // Raw registry stays in memory and a pipe. Python emits an allowlist only, atomically.
  const result = spawnSync(python, [publisher, output], {
    input: JSON.stringify(registry),
    encoding: "utf8",
    maxBuffer: 16384,
    timeout: 10000,
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1" },
  });
  requireSafe(!result.error && result.status === 0);
  return { ok: true };
}

export async function main(argv) {
  const options = {};
  for (let i = 0; i < argv.length; i++) {
    const flag = argv[i];
    if (flag === "--once") {
      options.once = true;
      continue;
    }
    requireSafe(
      [
        "--origin",
        "--token-file",
        "--output",
        "--python",
        "--interval",
      ].includes(flag) && argv[i + 1]
    );
    options[flag.slice(2)] = argv[++i];
  }
  requireSafe(options.origin && options["token-file"] && options.output);
  const interval = Number(options.interval ?? 60);
  requireSafe(Number.isInteger(interval) && interval >= 30 && interval <= 240);
  let stop = false;
  const controller = new AbortController();
  const halt = () => {
    stop = true;
    controller.abort();
  };
  process.once("SIGINT", halt);
  process.once("SIGTERM", halt);
  try {
    do {
      try {
        await refresh({
          origin: options.origin,
          tokenFile: options["token-file"],
          output: options.output,
          python: options.python,
        });
        process.stdout.write("Catalog snapshot refreshed\n");
      } catch (_) {
        // No raw exception, response, token, ticket, server config, or command output.
        process.stderr.write(
          "Catalog refresh failed; previous snapshot retained and will expire\n"
        );
        if (options.once) process.exitCode = 1;
      }
      if (options.once || stop) break;
      await delay(interval * 1000, undefined, {
        signal: controller.signal,
      }).catch(() => {});
    } while (!stop);
  } finally {
    process.removeListener("SIGINT", halt);
    process.removeListener("SIGTERM", halt);
  }
}
if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  main(process.argv.slice(2)).catch(() => {
    process.stderr.write("Invalid catalog producer configuration\n");
    process.exitCode = 1;
  });
}

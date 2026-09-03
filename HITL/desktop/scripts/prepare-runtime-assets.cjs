const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const rootDir = path.resolve(__dirname, "..");
const runtimeAssetsDir = path.join(rootDir, "runtime-assets");

function platformAssetKey() {
  const arch = process.arch === "arm64" ? "arm64" : "x64";
  return `${process.platform}-${arch}`;
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
  return dirPath;
}

function commandExists(command) {
  try {
    const lookup = process.platform === "win32" ? "where" : "which";
    return execFileSync(lookup, [command], { encoding: "utf8" }).split(/\r?\n/)[0].trim();
  } catch {
    return null;
  }
}

function copyTree(sourceDir, targetDir) {
  if (!fs.existsSync(sourceDir)) {
    throw new Error(`Source folder does not exist: ${sourceDir}`);
  }

  ensureDir(targetDir);
  for (const entry of fs.readdirSync(sourceDir, { withFileTypes: true })) {
    const sourcePath = path.join(sourceDir, entry.name);
    const targetPath = path.join(targetDir, entry.name);
    if (entry.isDirectory()) {
      copyTree(sourcePath, targetPath);
      continue;
    }
    if (!entry.isFile()) {
      continue;
    }

    ensureDir(path.dirname(targetPath));
    if (fs.existsSync(targetPath) && process.platform !== "win32") {
      fs.chmodSync(targetPath, 0o644);
    }
    fs.copyFileSync(sourcePath, targetPath);
    if (process.platform !== "win32") {
      fs.chmodSync(targetPath, (fs.statSync(sourcePath).mode | 0o200) & 0o777);
    }
  }
}

function copyFile(sourcePath, targetPath, mode) {
  if (!fs.existsSync(sourcePath)) {
    throw new Error(`Source file does not exist: ${sourcePath}`);
  }
  ensureDir(path.dirname(targetPath));
  if (fs.existsSync(targetPath) && process.platform !== "win32") {
    fs.chmodSync(targetPath, 0o644);
  }
  fs.copyFileSync(sourcePath, targetPath);
  if (mode !== undefined && process.platform !== "win32") {
    fs.chmodSync(targetPath, mode);
  }
}

function chmodExecutables(dirPath, executableNames) {
  if (process.platform === "win32") {
    return;
  }

  for (const name of executableNames) {
    const filePath = path.join(dirPath, name);
    if (fs.existsSync(filePath)) {
      fs.chmodSync(filePath, 0o755);
    }
  }
}

function ollamaRuntimeSource(sourcePath) {
  const resolvedSource = fs.realpathSync(sourcePath);
  const sourceDir = path.dirname(resolvedSource);
  const directRunner = path.join(sourceDir, "llama-server");
  const nestedRunner = path.join(sourceDir, "lib", "ollama", "llama-server");

  if (fs.existsSync(directRunner) || fs.existsSync(nestedRunner)) {
    return sourceDir;
  }
  return null;
}

function dirSizeBytes(dirPath) {
  if (!fs.existsSync(dirPath)) {
    return 0;
  }

  let total = 0;
  for (const entry of fs.readdirSync(dirPath, { withFileTypes: true })) {
    const entryPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      total += dirSizeBytes(entryPath);
    } else if (entry.isFile()) {
      total += fs.statSync(entryPath).size;
    }
  }
  return total;
}

function formatGb(bytes) {
  return `${(bytes / (1024 ** 3)).toFixed(2)} GB`;
}

function argValue(args, name) {
  const index = args.indexOf(name);
  return index === -1 ? null : args[index + 1];
}

function prepareOllamaExecutable(args) {
  const executableName = process.platform === "win32" ? "ollama.exe" : "ollama";
  const source = argValue(args, "--ollama-command") || process.env.HITL_OLLAMA_COMMAND || commandExists("ollama");
  if (!source) {
    console.log("Skipped Ollama executable: no local ollama command found.");
    return;
  }

  const target = path.join(runtimeAssetsDir, "ollama", platformAssetKey(), executableName);
  const runtimeSource = ollamaRuntimeSource(source);

  if (runtimeSource) {
    const targetDir = path.dirname(target);
    copyTree(runtimeSource, targetDir);
    chmodExecutables(targetDir, ["ollama", "llama-server", "llama-quantize"]);
    console.log(`Copied Ollama runtime to ${targetDir} (${formatGb(dirSizeBytes(targetDir))}).`);
    return;
  }

  copyFile(source, target, 0o755);
  console.log(`Copied Ollama executable to ${target}. Companion runtime files were not detected.`);
}

function prepareOllamaModels(args) {
  if (!args.includes("--include-models")) {
    console.log("Skipped Ollama model store. Pass --include-models to copy local model files.");
    return;
  }

  const source = argValue(args, "--model-store") || process.env.OLLAMA_MODELS || path.join(os.homedir(), ".ollama", "models");
  const target = path.join(runtimeAssetsDir, "ollama-models");
  copyTree(source, target);
  console.log(`Copied Ollama model store to ${target} (${formatGb(dirSizeBytes(target))}).`);
}

function prepareJavaRuntime(args) {
  const source = argValue(args, "--java-home") || process.env.HITL_JAVA_HOME;
  if (!source) {
    console.log("Skipped Java runtime. Pass --java-home or set HITL_JAVA_HOME to bundle a private JRE.");
    return;
  }

  const javaName = process.platform === "win32" ? "java.exe" : "java";
  const javaPath = path.join(source, "bin", javaName);
  if (!fs.existsSync(javaPath)) {
    throw new Error(`Java runtime is missing ${path.join("bin", javaName)}: ${source}`);
  }

  const target = path.join(runtimeAssetsDir, "jre", platformAssetKey());
  copyTree(source, target);
  console.log(`Copied Java runtime to ${target} (${formatGb(dirSizeBytes(target))}).`);
}

function main() {
  const args = process.argv.slice(2);
  prepareOllamaExecutable(args);
  prepareOllamaModels(args);
  prepareJavaRuntime(args);
}

main();

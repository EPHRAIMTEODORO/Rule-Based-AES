const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const desktopDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(desktopDir, "..", "..");
const hitlDir = path.join(repoRoot, "HITL");
const dataDir = path.join(repoRoot, "data");
const entryScript = path.join(hitlDir, "local_api_server.py");
const distPath = path.join(desktopDir, "backend-dist");
const buildPath = path.join(desktopDir, "backend-build");
const separator = process.platform === "win32" ? ";" : ":";

function pythonCommand() {
  if (process.env.HITL_PYTHON) {
    return process.env.HITL_PYTHON;
  }
  return process.platform === "win32" ? "python" : "python3";
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: options.capture ? "pipe" : "inherit",
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
      PYINSTALLER_CONFIG_DIR: path.join(buildPath, "pyinstaller-config"),
    },
  });

  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    const details = options.capture ? `\n${result.stdout || ""}${result.stderr || ""}` : "";
    throw new Error(`${command} ${args.join(" ")} failed with exit code ${result.status}.${details}`);
  }
  return result;
}

function moduleAvailable(command, moduleName) {
  const result = spawnSync(
    command,
    ["-c", `import importlib.util; raise SystemExit(0 if importlib.util.find_spec(${JSON.stringify(moduleName)}) else 1)`],
    { encoding: "utf8", stdio: "ignore" }
  );
  return result.status === 0;
}

function addDataArg(source, destination) {
  return `${source}${separator}${destination}`;
}

function main() {
  const python = pythonCommand();

  try {
    run(python, ["-m", "PyInstaller", "--version"], { capture: true });
  } catch (error) {
    console.error("PyInstaller is not installed for the selected Python runtime.");
    console.error(`Install it with: ${python} -m pip install pyinstaller`);
    console.error("Then rerun: npm run build:backend");
    process.exit(1);
  }

  const args = [
    "-m",
    "PyInstaller",
    "--clean",
    "--noconfirm",
    "--onedir",
    "--name",
    "hitl-api",
    "--distpath",
    distPath,
    "--workpath",
    path.join(buildPath, "work"),
    "--specpath",
    path.join(buildPath, "spec"),
    "--paths",
    repoRoot,
    "--add-data",
    addDataArg(path.join(hitlDir, "Essays.xlsx"), "HITL"),
    "--add-data",
    addDataArg(path.join(hitlDir, "ui", "index.html"), path.join("HITL", "ui")),
    "--add-data",
    addDataArg(path.join(dataDir, "awl_word_forms.json"), "data"),
    "--hidden-import",
    "HITL",
    "--hidden-import",
    "HITL.app_backend",
    "--hidden-import",
    "HITL.hitl_processor",
    "--hidden-import",
    "HITL.hybrid_llm_aes",
    "--hidden-import",
    "HITL.llm_rubric_prompt",
    "--hidden-import",
    "aes_feature_extractor",
    "--hidden-import",
    "lexical_diversity.lex_div",
    "--hidden-import",
    "nltk.tokenize.punkt",
    "--exclude-module",
    "spacy.tests",
    "--exclude-module",
    "nltk.test",
    "--exclude-module",
    "tkinter",
  ];

  const collectOptions = {
    spacy: [
      ["--collect-data", "spacy"],
      ["--collect-binaries", "spacy"],
      ["--collect-submodules", "spacy.lang.en"],
    ],
    en_core_web_sm: [["--collect-all", "en_core_web_sm"]],
    wordfreq: [["--collect-data", "wordfreq"]],
    language_tool_python: [["--collect-data", "language_tool_python"]],
    nltk: [["--collect-data", "nltk"]],
    openpyxl: [["--collect-data", "openpyxl"]],
  };

  for (const [moduleName, options] of Object.entries(collectOptions)) {
    if (moduleAvailable(python, moduleName)) {
      options.forEach((option) => args.push(...option));
    }
  }

  args.push(entryScript);

  fs.mkdirSync(distPath, { recursive: true });
  fs.mkdirSync(buildPath, { recursive: true });
  run(python, args);
}

main();

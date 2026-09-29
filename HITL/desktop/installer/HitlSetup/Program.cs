using System;
using System.Diagnostics;
using System.IO;

internal static class Program
{
    private const string AppFolderName = "hitl-academic-writing-scorer-desktop";
    private const string AppExeName = "HITL Academic Writing Scorer.exe";

    private static int Main()
    {
        string setupDir = AppDomain.CurrentDomain.BaseDirectory;
        string sevenZipPath = Path.Combine(setupDir, "7za.exe");
        string payloadPath = Path.Combine(setupDir, "hitl-app.7z");
        string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string appDir = Path.Combine(localAppData, "Programs", AppFolderName);
        string appExe = Path.Combine(appDir, AppExeName);

        Console.WriteLine("HITL Academic Writing Scorer installer");
        Console.WriteLine();

        if (!File.Exists(sevenZipPath))
        {
            return Fail("Missing installer helper: " + sevenZipPath);
        }

        if (!File.Exists(payloadPath))
        {
            return Fail("Missing installer payload: " + payloadPath);
        }

        Directory.CreateDirectory(appDir);
        Console.WriteLine("Installing to: " + appDir);
        Console.WriteLine("Extracting application files. This can take several minutes...");

        Process extract = Process.Start(new ProcessStartInfo
        {
            FileName = sevenZipPath,
            Arguments = "x \"" + payloadPath + "\" -o\"" + appDir + "\" -y",
            UseShellExecute = false
        });

        if (extract == null)
        {
            return Fail("Could not start 7-Zip extraction.");
        }

        extract.WaitForExit();
        if (extract.ExitCode != 0)
        {
            return Fail("7-Zip extraction failed with exit code " + extract.ExitCode + ".");
        }

        if (!File.Exists(appExe))
        {
            return Fail("Install finished, but the app executable is missing: " + appExe);
        }

        CreateShortcuts(appExe);

        Console.WriteLine();
        Console.WriteLine("Install complete.");
        Console.WriteLine("Launching HITL Academic Writing Scorer...");
        Process.Start(new ProcessStartInfo
        {
            FileName = appExe,
            WorkingDirectory = appDir,
            UseShellExecute = true
        });

        return 0;
    }

    private static void CreateShortcuts(string appExe)
    {
        string script =
            "$target = $args[0];" +
            "$work = Split-Path $target;" +
            "$ws = New-Object -ComObject WScript.Shell;" +
            "$links = @(" +
            "(Join-Path ([Environment]::GetFolderPath('Desktop')) 'HITL Academic Writing Scorer.lnk')," +
            "(Join-Path ([Environment]::GetFolderPath('Programs')) 'HITL Academic Writing Scorer.lnk')" +
            ");" +
            "foreach ($link in $links) {" +
            "$shortcut = $ws.CreateShortcut($link);" +
            "$shortcut.TargetPath = $target;" +
            "$shortcut.WorkingDirectory = $work;" +
            "$shortcut.IconLocation = \"$target,0\";" +
            "$shortcut.Save();" +
            "}";

        ProcessStartInfo startInfo = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = "-NoProfile -ExecutionPolicy Bypass -Command \"" + script.Replace("\"", "\\\"") + "\" \"" + appExe + "\"",
            UseShellExecute = false,
            CreateNoWindow = true
        };

        Process process = Process.Start(startInfo);
        if (process != null)
        {
            process.WaitForExit();
        }
    }

    private static int Fail(string message)
    {
        Console.Error.WriteLine(message);
        Console.Error.WriteLine();
        Console.Error.WriteLine("Press Enter to close.");
        Console.ReadLine();
        return 1;
    }
}

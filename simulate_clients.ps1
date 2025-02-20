param (
    [int]$numClients = 10  # Par défaut, 10 clients
)

# Charger les bibliothèques nécessaires
Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class User32 {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@ -Language CSharp

function Set-WindowFocus($processName) {
    Start-Sleep -Seconds 1
    $proc = Get-Process | Where-Object { $_.ProcessName -like $processName } | Select-Object -First 1
    if ($proc -and $proc.MainWindowHandle -ne 0) {
        [User32]::SetForegroundWindow($proc.MainWindowHandle)
        Start-Sleep -Milliseconds 500
    }
}

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class Keyboard {
    [DllImport("user32.dll", SetLastError = true)]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);
    public static void SendKey(byte key) {
        keybd_event(key, 0, 0, UIntPtr.Zero);
        keybd_event(key, 0, 2, UIntPtr.Zero); // KEYUP
    }
}
"@ -Language CSharp

# Liste de touches disponibles (A-Z, limité à 26 max)
$keys = @(0x41..0x5A)  # A à Z (codes virtuels)
$VK_ENTER = 0x0D

# Démarrer le serveur
Start-Process powershell -ArgumentList "-NoExit", "-Command `"cd ..\..\programs\i_like_trains\; ./venv/Scripts/activate; python server/server.py`""
Start-Sleep -Seconds 3

# Ouvrir les clients et envoyer les touches
$scriptPath = "cd ..\..\programs\i_like_trains\; ./venv/Scripts/activate; python client.py"
for ($i = 0; $i -lt $numClients; $i++) {
    $key = $keys[$i % $keys.Length]  # Boucle sur les lettres si plus de 26 clients

    # Lancer une nouvelle fenêtre client
    Start-Process powershell -PassThru -ArgumentList "-NoExit", "-Command `"$scriptPath`""

    # Pause pour s'assurer que la fenêtre est bien ouverte
    Start-Sleep -Seconds 1

    # Donner le focus à la console client
    Set-WindowFocus "powershell"

    # Envoyer la touche et "Enter"
    Start-Sleep -Milliseconds 500
    [Keyboard]::SendKey($key)
    Start-Sleep -Milliseconds 200
    [Keyboard]::SendKey($VK_ENTER)

    Start-Sleep -Milliseconds 300
}

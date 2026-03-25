Dim shell, args, scriptPath, command, exitCode

Set shell = CreateObject("WScript.Shell")
Set args = WScript.Arguments

If args.Count < 1 Then
    WScript.Quit 1
End If

scriptPath = args.Item(0)
command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & scriptPath & """"

exitCode = shell.Run(command, 0, True)
WScript.Quit exitCode

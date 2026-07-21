Option Explicit
On Error Resume Next

Function QuoteArg(ByVal value)
    QuoteArg = Chr(34) & CStr(value) & Chr(34)
End Function

If WScript.Arguments.Count <> 10 Then
    WScript.Quit 64
End If

Dim shell, powershell, runner, policy, config, repoRoot, schema, authFile
Dim pythonExe, timeoutSeconds, maxAttempts, retrySeconds, command, exitCode

Set shell = CreateObject("WScript.Shell")
If Err.Number <> 0 Then
    WScript.Quit 70
End If

powershell = shell.ExpandEnvironmentStrings( _
    "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe")
runner = WScript.Arguments(0)
policy = WScript.Arguments(1)
config = WScript.Arguments(2)
repoRoot = WScript.Arguments(3)
schema = WScript.Arguments(4)
authFile = WScript.Arguments(5)
pythonExe = WScript.Arguments(6)
timeoutSeconds = WScript.Arguments(7)
maxAttempts = WScript.Arguments(8)
retrySeconds = WScript.Arguments(9)

If InStr(runner & policy & config & repoRoot & schema & authFile & pythonExe, Chr(34)) > 0 Then
    WScript.Quit 64
End If
If Not IsNumeric(timeoutSeconds) Or Not IsNumeric(maxAttempts) Or Not IsNumeric(retrySeconds) Then
    WScript.Quit 64
End If
timeoutSeconds = CStr(CLng(timeoutSeconds))
maxAttempts = CStr(CLng(maxAttempts))
retrySeconds = CStr(CLng(retrySeconds))

command = QuoteArg(powershell) & _
    " -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File " & _
    QuoteArg(runner) & " -PolicyPath " & QuoteArg(policy) & _
    " -ConfigPath " & QuoteArg(config) & _
    " -RepoRoot " & QuoteArg(repoRoot) & _
    " -SchemaPath " & QuoteArg(schema) & _
    " -CodexAuthFile " & QuoteArg(authFile) & _
    " -PythonExe " & QuoteArg(pythonExe) & _
    " -TimeoutSeconds " & timeoutSeconds & _
    " -MaxAttempts " & maxAttempts & _
    " -RetryBaseSeconds " & retrySeconds

Err.Clear
exitCode = shell.Run(command, 0, True)
If Err.Number <> 0 Then
    WScript.Quit 70
End If
WScript.Quit exitCode

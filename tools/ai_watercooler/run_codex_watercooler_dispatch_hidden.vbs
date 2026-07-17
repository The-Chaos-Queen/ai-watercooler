Option Explicit
On Error Resume Next

Function QuoteArg(ByVal value)
    QuoteArg = Chr(34) & CStr(value) & Chr(34)
End Function

If WScript.Arguments.Count <> 5 Then
    WScript.Quit 64
End If

Dim shell, powershell, runner, policy, timeoutSeconds, maxAttempts, retrySeconds
Dim command, exitCode

Set shell = CreateObject("WScript.Shell")
If Err.Number <> 0 Then
    WScript.Quit 70
End If

powershell = shell.ExpandEnvironmentStrings( _
    "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe")
runner = WScript.Arguments(0)
policy = WScript.Arguments(1)
timeoutSeconds = WScript.Arguments(2)
maxAttempts = WScript.Arguments(3)
retrySeconds = WScript.Arguments(4)

If InStr(runner, Chr(34)) > 0 Or InStr(policy, Chr(34)) > 0 Then
    WScript.Quit 64
End If

command = QuoteArg(powershell) & _
    " -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File " & _
    QuoteArg(runner) & " -PolicyPath " & QuoteArg(policy) & _
    " -TimeoutSeconds " & timeoutSeconds & _
    " -MaxAttempts " & maxAttempts & _
    " -RetryBaseSeconds " & retrySeconds

Err.Clear
exitCode = shell.Run(command, 0, True)
If Err.Number <> 0 Then
    WScript.Quit 70
End If
WScript.Quit exitCode

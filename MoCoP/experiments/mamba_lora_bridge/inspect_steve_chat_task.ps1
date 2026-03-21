$taskName = "MoCoP Steve Chat"

$task = Get-ScheduledTask -TaskName $taskName
$info = Get-ScheduledTaskInfo -TaskName $taskName

[pscustomobject]@{
    TaskName = $task.TaskName
    TaskPath = $task.TaskPath
    State = $task.State
    LastRunTime = $info.LastRunTime
    LastTaskResult = $info.LastTaskResult
    Execute = $task.Actions.Execute
    Arguments = $task.Actions.Arguments
} | Format-List

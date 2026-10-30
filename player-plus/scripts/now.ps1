# now.ps1 — the clock is read, never computed. Prints the moment in local time and UTC
# (the PowerShell twin of scripts/now, same two lines).
$utf8 = New-Object System.Text.UTF8Encoding($false)
try { [Console]::OutputEncoding = $utf8 } catch {}
$now = Get-Date; $tz = [TimeZoneInfo]::Local
$zone = if ($tz.IsDaylightSavingTime($now)) { $tz.DaylightName } else { $tz.StandardName }
[Console]::Out.WriteLine($now.ToString('dddd, MMMM dd, yyyy') + ' ' + [char]0x2014 + ' ' + $now.ToString('HH:mm') + " $zone")
[Console]::Out.WriteLine([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mmZ'))

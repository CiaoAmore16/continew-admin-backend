$ErrorActionPreference = 'Continue'
$log = 'C:\Users\三纪\Desktop\continew-admin-dev\mysql-reset.log'
Set-Content -Path $log -Value '=== mysql password reset ==='

$bin = 'C:\Program Files\MySQL\MySQL Server 9.1\bin'
$mysqld = Join-Path $bin 'mysqld.exe'
$mysql  = Join-Path $bin 'mysql.exe'
$defaults = 'C:\ProgramData\MySQL\MySQL Server 9.1\my.ini'
$initFile = 'C:\mysql-init.txt'
$outFile = 'C:\Users\三纪\Desktop\continew-admin-dev\mysqld-out.log'
$errFile = 'C:\Users\三纪\Desktop\continew-admin-dev\mysqld-err.log'

Add-Content $log '1. stop service'
Stop-Service -Name 'MySQL91' -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

Add-Content $log '2. write init file'
Set-Content -Path $initFile -Value "ALTER USER 'root'@'localhost' IDENTIFIED BY '123456';" -Encoding ASCII

Add-Content $log '3. start mysqld with init-file'
$p = Start-Process -FilePath $mysqld -ArgumentList @("--defaults-file=`"$defaults`"", "--init-file=$initFile", '--console') -PassThru -WindowStyle Hidden -RedirectStandardOutput $outFile -RedirectStandardError $errFile
Add-Content $log ("mysqld started pid=" + $p.Id)

Add-Content $log '4. wait for ready (poll root/123456)'
$ready = $false
for ($i=0; $i -lt 40; $i++) {
  Start-Sleep -Seconds 3
  & $mysql -uroot -p123456 -h127.0.0.1 -P3306 -e 'SELECT 1' *> $null
  if ($LASTEXITCODE -eq 0) { $ready = $true; Add-Content $log ("ready at iter " + $i); break }
}
if (-not $ready) { Add-Content $log 'TIMEOUT waiting for mysqld' }

Add-Content $log '5. shutdown mysqld'
& $mysql -uroot -p123456 -h127.0.0.1 -P3306 -e 'SHUTDOWN' *> $null
Start-Sleep -Seconds 5

Add-Content $log '6. start service'
Start-Service -Name 'MySQL91'
Start-Sleep -Seconds 3

Add-Content $log '7. cleanup init file'
Remove-Item $initFile -Force -ErrorAction SilentlyContinue

Add-Content $log '=== done ==='

param()

[System.Reflection.Assembly]::LoadWithPartialName("System.IO.Compression.FileSystem") | Out-Null

function Read-EnterpriseSheet {
    param([string]$FilePath)
        if ([string]::IsNullOrWhiteSpace($FilePath) -or -not (Test-Path -LiteralPath $FilePath)) {
        $found = Get-ChildItem -Path "$env:USERPROFILE\Downloads" -Filter "*Auto-MDS (3)*" | Select-Object -First 1
        if ($found) { $FilePath = $found.FullName }
    }
    
    $fullPath = (Get-Item $FilePath).FullName
    $zip = [System.IO.Compression.ZipFile]::OpenRead($fullPath)
    
    # Read shared strings
    $ssEntry = $zip.GetEntry("xl/sharedStrings.xml")
    $stream = $ssEntry.Open()
    $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::UTF8)
    $ssXml = [xml]$reader.ReadToEnd()
    $reader.Close()
    $stream.Close()
    
    $sharedStrings = New-Object System.Collections.Generic.List[string]
    foreach ($si in $ssXml.sst.si) {
        $sharedStrings.Add($si.InnerText)
    }
    
    # Read sheet2.xml (Enterprise)
    $sEntry = $zip.GetEntry("xl/worksheets/sheet2.xml")
    $stream = $sEntry.Open()
    $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::UTF8)
    $sXml = [xml]$reader.ReadToEnd()
    $reader.Close()
    $stream.Close()
    $zip.Dispose()
    
    $rows = $sXml.worksheet.sheetData.row
    $currentModule = "Chua phan loai"
    $testcases = @()
    
    foreach ($r in $rows) {
        $rowNum = [int]$r.r
        $cells = @{}
        foreach ($c in $r.c) {
            $colLetter = $c.r -replace '\d+'
            $val = ""
            if ($c.v) {
                $raw = $c.v
                if ($c.t -eq "s") {
                    $val = $sharedStrings[[int]$raw]
                } else {
                    $val = $raw
                }
            }
            $cells[$colLetter] = $val
        }
        
        $colA = if ($cells.ContainsKey("A")) { $cells["A"].Trim() } else { "" }
        $colB = if ($cells.ContainsKey("B")) { $cells["B"].Trim() } else { "" }
        
        if ($colB -match "PHAN HE|Phan he|PHÂN HỆ|Phân hệ") {
            $currentModule = $colB.Trim()
        } elseif ($colA -match "PHAN HE|Phan he|PHÂN HỆ|Phân hệ") {
            $currentModule = $colA.Trim()
        }
        
        if ($colA -match '^TC[-_]?\d+') {
            $testcases += [PSCustomObject]@{
                Row = $rowNum
                Module = $currentModule
                ID = $colA
                Name = if ($cells.ContainsKey("B")) { $cells["B"].Trim() } else { "" }
                PreCondition = if ($cells.ContainsKey("C")) { $cells["C"].Trim() } else { "" }
                Steps = if ($cells.ContainsKey("D")) { $cells["D"].Trim() } else { "" }
                DataTest = if ($cells.ContainsKey("E")) { $cells["E"].Trim() } else { "" }
                Expected = if ($cells.ContainsKey("F")) { $cells["F"].Trim() } else { "" }
                Progress = if ($cells.ContainsKey("G")) { $cells["G"].Trim() } else { "" }
                Status = if ($cells.ContainsKey("H")) { $cells["H"].Trim() } else { "" }
                QC = if ($cells.ContainsKey("I")) { $cells["I"].Trim() } else { "" }
            }
        }
    }
    return $testcases
}

# Stdio JSON-RPC Loop
$inputReader = [System.Console]::In
while (($line = $inputReader.ReadLine()) -ne $null) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
        $req = $line | ConvertFrom-Json
        $id = $req.id
        $method = $req.method
        
        if ($method -eq "initialize") {
            $resp = @{
                jsonrpc = "2.0"
                id = $id
                result = @{
                    protocolVersion = "2024-11-05"
                    capabilities = @{ tools = @{} }
                    serverInfo = @{ name = "excel-Enterprise-mcp-server"; version = "1.0.0" }
                }
            }
            [System.Console]::Out.WriteLine(($resp | ConvertTo-Json -Compress -Depth 10))
        } elseif ($method -eq "notifications/initialized") {
        } elseif ($method -eq "ping") {
            $resp = @{ jsonrpc = "2.0"; id = $id; result = @{} }
            [System.Console]::Out.WriteLine(($resp | ConvertTo-Json -Compress))
        } elseif ($method -eq "tools/list") {
            $resp = @{
                jsonrpc = "2.0"
                id = $id
                result = @{
                    tools = @(
                        @{
                            name = "read_Enterprise_sheet"
                            description = "Doc toan bo testcase tu sheet Enterprise cua file Excel"
                            inputSchema = @{
                                type = "object"
                                properties = @{
                                    file_path = @{ type = "string"; description = "Duong dan file Excel" }
                                }
                            }
                        }
                    )
                }
            }
            [System.Console]::Out.WriteLine(($resp | ConvertTo-Json -Compress -Depth 10))
        } elseif ($method -eq "tools/call") {
            $toolName = $req.params.name
            if ($toolName -eq "read_Enterprise_sheet") {
                $fPath = $req.params.arguments.file_path
                $tcs = Read-EnterpriseSheet -FilePath $fPath
                $textResult = $tcs | ConvertTo-Json -Depth 5
                $resp = @{
                    jsonrpc = "2.0"
                    id = $id
                    result = @{
                        content = @(
                            @{ type = "text"; text = $textResult }
                        )
                    }
                }
                [System.Console]::Out.WriteLine(($resp | ConvertTo-Json -Compress -Depth 10))
            } else {
                $resp = @{
                    jsonrpc = "2.0"
                    id = $id
                    error = @{ code = -32601; message = "Method not found" }
                }
                [System.Console]::Out.WriteLine(($resp | ConvertTo-Json -Compress))
            }
        }
    } catch {
    }
}
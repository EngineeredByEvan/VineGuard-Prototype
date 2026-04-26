param(
  [Parameter(Mandatory=$true)][string]$Serial,
  [string]$Manifest = "firmware/esp32-node/tools/provisioning_manifest.csv"
)
python firmware/esp32-node/tools/make_keys_header.py --manifest $Manifest --serial $Serial
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
pio run -d firmware/esp32-node -e heltec_wifi_lora_32_V3 -t upload
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$row = Import-Csv $Manifest | Where-Object { $_.serial -eq $Serial } | Select-Object -First 1
if (-not $row) { throw "Serial not found in manifest: $Serial" }
Write-Host "Label this node: serial=$($row.serial) device_id=$($row.device_id) dev_eui=$($row.dev_eui)"

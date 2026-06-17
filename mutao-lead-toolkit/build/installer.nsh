!macro customInit
  nsExec::ExecToLog 'taskkill /F /T /IM "木桃工具包.exe"'
  nsExec::ExecToLog 'taskkill /F /T /IM "灵数工具包.exe"'
  nsExec::ExecToLog 'taskkill /F /T /IM "获客工具包.exe"'
  Sleep 800
!macroend

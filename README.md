# Subsync-headless

Asynchronously execute subsync jobs put in config/subsync/jobs. 
Each job is a file containing the subsync command to execute.
This tool is meant to be used as postprocessing for Bazarr, an example of command is:
```
echo "subsync --cli --verbose 2 sync 
--ref \"{{episode}}\" --ref-stream-by-type audio --ref-lang \"{{episode_language_code3}}\" 
--sub \"{{subtitles}}\" --sub-lang \"{{subtitles_language_code3}}\" 
--out \"{{subtitles}}\" --overwrite --effort .75 --jobs 0 --window-size 1800" 
> "/subsync/{{episode_name}}.{{subtitles_language_code3}}.job";
```
With the Bazarr subsync folder referencing the config/subsync/jobs folder.

I made this tool to avoid duplicating post-processing in case of two discovery jobs being launched by Bazarr, which happen often.
Because the job file has a unique name and is removed only when finished processing, we have a sort of lock file preventing this issue.
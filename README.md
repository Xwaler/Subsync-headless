# Subsync-headless

Asynchronously execute subsync jobs put in config/subsync/jobs. 
Each job is a file containing the subsync command to execute.
This tool is meant to be used as postprocessing for Bazarr with the command:
```
echo "{
\"ref\": \"{{episode}}\", \"ref_lang\": \"{{episode_language_code3}}\", 
\"sub\": \"{{subtitles}}\", \"sub_lang\": \"{{subtitles_language_code3}}\",
\"sub_code_2\": \"{{subtitles_language_code2}}\", \"sub_id\": \"{{subtitle_id}}\", 
\"provider\": \"{{provider}}\", \"series_id\": \"{{series_id}}\", \"episode_id\": \"{{episode_id}}\"
}" > "/subsync/{{episode_name}}.{{subtitles_language_code3}}.json";
```
With the Bazarr subsync folder referencing the config/subsync/jobs folder.

I made this tool to avoid duplicating post-processing in case of two discovery jobs being launched by Bazarr, which happen often.
Because the job file has a unique name and is removed only when finished processing, we have a sort of lock file preventing this issue.
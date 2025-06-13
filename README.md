julo v1.2.1 - jumping loader

Loads online videos from sites which require serveral transitions from
one site page to another before video becomes available.

The program searches in the current directory for the config file,
takes settings for the site from the config file and starts searching
the site contents for the direct url to the target file. After the
program makes several jumps to internal site pages (if any) the direct
url to the target file is found and the program starts to download the
target file. The target file is loading to the temporary file with a
unique name and may be resumed in another download session. After the
file has been downloaded, it is renamed to the ready name with a
number in order and a message is displayed to the desktop. Also the
file url is marked as downloaded when the file has been downloaded.

Here is the config file structure:

    <?xml version="1.0" encoding="utf‐8"?>
    <site name="">
      <urls file="" search="" replace="" />
      <notice name="" one="" all="" />
      <patterns>
        <pattern load=""
                 start=""
                 left=""
                 right="" />
        <pattern load=""
                 start=""
                 left=""
                 right="" />

        ...

      </patterns>
      <load cmd="" />
      <temp prefix="" suffix="" random="" />
      <final prefix="" suffix="" />
    </site>

Fields:

    site name     ‐‐ which name to display in the console
    urls file     ‐‐ name of file with top urls
    urls search   ‐‐ marker for urls in the urls file marked for download
    urls replace  ‐‐ marker in the urls file for downloaded urls
    notice name   ‐‐ which name to display in the displayed download notice
    notice one    ‐‐ which message to display in the displayed download notice
                     when one file has been complete
    notice all    ‐‐ which message to display in the displayed download notice
                     when all files have been complete
    pattern load  ‐‐ which command for loading the page to run
                     with %url argument
    pattern start ‐‐ which regexp should match in the loaded page
                     for start searching the url in the page
    pattern left  ‐‐ which regexp should match in the loaded page
                     at the left side of the url
    pattern right ‐‐ which regexp should match in the loaded page
                     at the right side of the url
    load cmd      ‐‐ which command for loading the target file
                     with %url and %file arguments
    temp prefix   ‐‐ which prefix to use in the temporary file name
    temp suffix   ‐‐ which suffix to use in the temporary file name
    temp random   ‐‐ the length of the random hexadecimal number
                     in the temporary file name
                     unique and constant for the according target url
    final prefix  ‐‐ which prefix to use in the complete file name
    final suffix  ‐‐ which suffix to use in the complete file name

Example:

    File julo.xml:

    <?xml version="1.0" encoding="utf‐8"?>
    <site name="Site With Videos">
      <urls file="urls.txt" search="*" replace="[" />
      <notice name="SWV" one="loaded" all="complete" />
      <patterns>
        <pattern load="curl %url"
                 start="Press download button..."
                 left="&lt;a href=&quot;"
                 right="&quot; class" />
      </patterns>
      <temp prefix="tmp_" suffix=".mp4" random="8" />
      <final prefix="file" suffix=".mp4" />
      <load cmd="curl %url ‐o %file" />
    </site>

    File urls.txt:

    *https://www.sitewithvideos.com/some‐interesting‐topic1.html
    *https://www.sitewithvideos.com/some‐interesting‐topic2.html
    *https://www.sitewithvideos.com/some‐interesting‐topic3.html

Example of the YouTube configuration:

File julo.xml:

    <?xml version="1.0" encoding="utf‐8"?>
    <site name="YouTube">
      <urls file="urls" search="*" replace="[" />
      <notice name="YouTube" one="one loaded" all="all loaded" />
      <patterns />
      <load cmd="yt‐dlp ‐c ‐‐proxy socks5://localhost:1080 %url ‐o %file" />
      <temp prefix="yt_tmp_" suffix=".mp4" random="8" />
      <final prefix="yt_vid_" suffix=".mp4" />
    </site>

File urls.txt:

    YouTube urls

    Cat plays
    [https://www.youtube.com/watch?v=wJHnone1JiU
    Driving a car
    *https://www.youtube.com/watch?v=wJHnone2JiU
    Some song
    [https://www.youtube.com/watch?v=wJHnone3JiU
    A lesson
    *https://www.youtube.com/watch?v=wJHnone4JiU

Output files:

    yt_vid_1.mp4
    yt_vid_2.mp4
    yt_vid_3.mp4
    yt_vid_4.mp4

Here  you  see  how  to  load videos from YouTube by the program yt‐dlp and some
tricks within the command line without jumps by patterns for pages.

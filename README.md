# julo

jumping loader

Loads online videos from sites which require several transitions from
one site page to another before video becomes available.

---

### Requirements


This program has tested on environment configuration
```
  Linux Fedora 39
  Python 3.12.0
  GNU bash 5.2.15
  curl 8.2.1
```

### Building

Build the docs and read the README file in _build/docs_.

To build run:

```sh
$ ./configure
$ make
```

### Testing

To test run:

```sh
$ make tests
```

### Installation

To install run:

```sh
$ sudo make install
```

To uninstall run:

```sh
$ sudo make uninstall
```

### Set program config

Read examples in __man 5 julo__ .

### Run

Make the config file __julo.xml__ in the directory. Make the urls file in the directory. In the urls file mark urls you want to download.

After that in this directory run:

```sh
$ julo
```

---

julo v1.3.0 - jumping loader

Loads online videos from sites which require serveral transitions from
one site page to another before video becomes available.

The  program  searches  in the current directory for the config file, takes set-
tings for the site from the config file and starts searching the  site  contents
for  the direct url to the target file. After the program makes several jumps to
internal site pages (if any) the direct url to the target file is found and  the
program  starts  to  download the target file. The target file is loading to the
temporary file with a unique name and may be resumed in  another  download  ses-
sion. After the file has been downloaded, it is renamed to the ready name with a
number  in order or to the fixed name and a message is displayed to the desktop.
Also the file url is marked as downloaded when the file has been downloaded.

       Here is the config file structure:

           <?xml version="1.0" encoding="utf-8"?>
           <site name="">
             <urls file="" search="" replace="" namesep="" />
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

           site name     -- which name to display in the console
           urls file     -- name of file with top urls
           urls search   -- marker for urls in the urls file marked for download
           urls replace  -- marker in the urls file for downloaded urls
           urls namesep  -- name separator for the fixed file name
           notice name   -- which name to display in the displayed download notice
           notice one    -- which message to display in the displayed download notice
                            when one file has been complete
                            can hold %file for display file name in the message
           notice all    -- which message to display in the displayed download notice
                            when all files have been complete
           pattern load  -- which command for loading the page to run
                            with %url argument
           pattern start -- which regexp should match in the loaded page
                            for start searching the url in the page
           pattern left  -- which regexp should match in the loaded page
                            at the left side of the url
           pattern right -- which regexp should match in the loaded page
                            at the right side of the url
           load cmd      -- which command for loading the target file
                            with %url and %file arguments
           temp prefix   -- which prefix to use in the temporary file name
           temp suffix   -- which suffix to use in the temporary file name
           temp random   -- the length of the random hexadecimal number
                            in the temporary file name
                            unique and constant for the according target url
           final prefix  -- which prefix to use in the complete file name
           final suffix  -- which suffix to use in the complete file name

       Example:

       File julo.xml:

           <?xml version="1.0" encoding="utf-8"?>
           <site name="Site With Videos">
             <urls file="urls.txt" search="*" replace="[" namesep=" " />
             <notice name="SWV" one="loaded" all="complete" />
             <patterns>
               <pattern load="curl %url"
                        start="Press download button..."
                        left="&lt;a href=&quot;"
                        right="&quot; class" />
             </patterns>
             <temp prefix="tmp_" suffix=".mp4" random="8" />
             <final prefix="file" suffix=".mp4" />
             <load cmd="curl %url -o %file" />
           </site>

       File urls.txt:

           *https://www.sitewithvideos.com/some-interesting-topic1.html
           *https://www.sitewithvideos.com/some-interesting-topic2.html
           *https://www.sitewithvideos.com/some-interesting-topic3.html

       Output files:

           file1.mp4
           file2.mp4
           file3.mp4

With  these  settings the program will display "Site With Videos" to the user in
the console. Then the program will start search in the file "urls.txt" for  urls
starting from the "\*" character. And then the url will be downloaded by the com-
mand  "curl %url"  where the page url will be substituted to the "%url" template
point and the downloaded resulting page will be searched for  the  start  string
"Press download button...". If the start string is found, then the page text af-
ter  the start string will be searched for the left pattern ’<a href="’ which is
starting the target url and ’" class’ for the right pattern which is ending  the
target  url.  Then  the  target  url will be found and downloaded by the command
"curl %url -o %file" where the target url will be substituted to the "%url" tem-
plate point and the output file name will be substituted to the "%file" template
point. The target file will download to the  temporary  name  "tmp_abcd0102.mp4"
and  when  the  download of the target file will be completed the temporary file
will be renamed from "tmp_abcd0102.mp4" to "file1.mp4". Then in  the  "urls.txt"
the  top  url will be marked from "\*" character to the "[" character and the no-
tice will be displayed to the user as "SWV: loaded". If  no  any  top  urls  are
marked in the file "urls.txt" for download by the "\*" character, then the notice
will be displayed to the user as "SWV: complete" also.

Download from YouTube configuration:

File julo.xml:

    <?xml version="1.0" encoding="utf-8"?>
    <site name="YouTube">
      <urls file="urls" search="*" replace="[" namesep=" " />
      <notice name="YouTube" one="loaded %file" all="all loaded" />
      <patterns />
      <load cmd="yt-dlp -c --proxy socks5://localhost:1080 %url -o %file" />
      <temp prefix="yt_tmp_" suffix=".mp4" random="8" />
      <final prefix="yt_vid_" suffix=".mp4" />
    </site>

File urls.txt:

    YouTube urls

    Cat plays
    *https://www.youtube.com/watch?v=wJHnone1JiU
    Driving a car
    *https://www.youtube.com/watch?v=wJHnone2JiU
    Some song
    *https://www.youtube.com/watch?v=wJHnone3JiU
    A lesson
    *https://www.youtube.com/watch?v=wJHnone4JiU lesson.mp4

Output files:

    yt_vid_1.mp4
    yt_vid_2.mp4
    yt_vid_3.mp4
    lesson.mp4

Output messages:

    YouTube: loaded yt_vid_1.mp4
    YouTube: loaded yt_vid_2.mp4
    YouTube: loaded yt_vid_3.mp4
    YouTube: loaded lesson.mp4
    YouTube: all loaded

Here you see how to load videos from YouTube by the program yt-dlp and some
tricks within the command line without jumps by patterns for pages. First three
videos are saved by the order and the fourth video is saved by the fixed name.

const { spawn } = require('child_process');
const ffmpegPath = require('ffmpeg-static');

console.log('FFmpeg path:', ffmpegPath);

const videoInput = './REC-20260504133020.mp4';
const audioInput = './新录音 20.m4a';
const trimStart = '102';
const outputBase = './short_';

const shorts = [
  { start: 0, duration: 60, filename: 'part1.mp4' },
  { start: 60, duration: 60, filename: 'part2.mp4' },
  { start: 120, duration: 60, filename: 'part3.mp4' },
  { start: 180, duration: 60, filename: 'part4.mp4' },
  { start: 240, duration: 60, filename: 'part5.mp4' },
];

function trimAndBlurVideo() {
  return new Promise((resolve, reject) => {
    const blurredVideo = './blurred_video.mp4';
    const ffmpeg = spawn(ffmpegPath, [
      '-y',
      '-i', videoInput,
      '-ss', trimStart,
      '-vf', 'boxblur=5:3',
      '-c:v', 'libx264',
      '-crf', '23',
      '-c:a', 'copy',
      blurredVideo
    ]);

    ffmpeg.stderr.on('data', (data) => {
      console.error(`blur stderr: ${data}`);
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        console.log(`Successfully blurred video`);
        resolve(blurredVideo);
      } else {
        reject(new Error(`Blur process exited with code ${code}`));
      }
    });
  });
}

function mergeWithAudio(videoFile, outputFile) {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn(ffmpegPath, [
      '-y',
      '-i', videoFile,
      '-i', audioInput,
      '-c:v', 'copy',
      '-c:a', 'aac',
      '-strict', 'experimental',
      '-map', '0:v:0',
      '-map', '1:a:0',
      '-shortest',
      outputFile
    ]);

    ffmpeg.stderr.on('data', (data) => {
      console.error(`merge stderr: ${data}`);
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        console.log(`Successfully merged into ${outputFile}`);
        resolve();
      } else {
        reject(new Error(`Merge process exited with code ${code}`));
      }
    });
  });
}

function splitIntoShorts(blurredVideo) {
  return Promise.all(shorts.map((short, index) => {
    return new Promise((resolve, reject) => {
      const outputFile = outputBase + short.filename;
      const ffmpeg = spawn(ffmpegPath, [
        '-y',
        '-i', blurredVideo,
        '-ss', short.start.toString(),
        '-t', short.duration.toString(),
        '-c:v', 'copy',
        '-c:a', 'copy',
        outputFile
      ]);

      ffmpeg.stderr.on('data', (data) => {
        console.error(`split ${index + 1} stderr: ${data}`);
      });

      ffmpeg.on('close', (code) => {
        if (code === 0) {
          console.log(`Successfully created ${outputFile}`);
          resolve(outputFile);
        } else {
          reject(new Error(`Split process for part ${index + 1} exited with code ${code}`));
        }
      });
    });
  }));
}

async function run() {
  try {
    console.log('Step 1: Trimming and blurring video...');
    const blurredVideo = await trimAndBlurVideo();
    
    console.log('Step 2: Merging with audio...');
    const mergedVideo = './blurred_merged.mp4';
    await mergeWithAudio(blurredVideo, mergedVideo);
    
    console.log('Step 3: Splitting into short videos...');
    await splitIntoShorts(mergedVideo);
    
    console.log('All done!');
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

run();
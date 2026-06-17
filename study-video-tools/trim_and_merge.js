const { spawn } = require('child_process');
const ffmpegPath = require('ffmpeg-static');

console.log('FFmpeg path:', ffmpegPath);

const videoInput = './REC-20260504133020.mp4';
const audioInput = './新录音 20.m4a';
const trimmedVideo = './trimmed_video.mp4';
const output = './final_output.mp4';

const trimStart = '102';

function trimVideo() {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn(ffmpegPath, [
      '-y',
      '-i', videoInput,
      '-ss', trimStart,
      '-c:v', 'copy',
      '-c:a', 'copy',
      trimmedVideo
    ]);

    ffmpeg.stderr.on('data', (data) => {
      console.error(`trim stderr: ${data}`);
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        console.log(`Successfully trimmed video (removed first ${trimStart} seconds)`);
        resolve();
      } else {
        reject(new Error(`Trim process exited with code ${code}`));
      }
    });
  });
}

function mergeVideoAudio() {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn(ffmpegPath, [
      '-y',
      '-i', trimmedVideo,
      '-i', audioInput,
      '-c:v', 'copy',
      '-c:a', 'aac',
      '-strict', 'experimental',
      '-map', '0:v:0',
      '-map', '1:a:0',
      '-shortest',
      output
    ]);

    ffmpeg.stderr.on('data', (data) => {
      console.error(`merge stderr: ${data}`);
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        console.log(`Successfully merged into ${output}`);
        resolve();
      } else {
        reject(new Error(`Merge process exited with code ${code}`));
      }
    });
  });
}

async function run() {
  try {
    await trimVideo();
    await mergeVideoAudio();
    console.log('All done!');
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

run();
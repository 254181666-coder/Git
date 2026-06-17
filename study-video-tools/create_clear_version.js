const { spawn } = require('child_process');
const ffmpegPath = require('ffmpeg-static');

console.log('FFmpeg path:', ffmpegPath);

const videoInput = './REC-20260504133020.mp4';
const audioInput = './新录音 20.m4a';
const trimStart = '102';
const output = './clear_full_version.mp4';

async function run() {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn(ffmpegPath, [
      '-y',
      '-i', videoInput,
      '-ss', trimStart,
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
      console.error(`stderr: ${data}`);
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        console.log(`Successfully created clear version: ${output}`);
        resolve();
      } else {
        reject(new Error(`Process exited with code ${code}`));
      }
    });
  });
}

run().catch(console.error);
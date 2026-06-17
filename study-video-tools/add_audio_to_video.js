const { spawn } = require('child_process');
const ffmpegPath = require('ffmpeg-static');

console.log('FFmpeg path:', ffmpegPath);

const videoInput = './merged_wxapp.mp4';
const audioInput = './小程序配音.m4a';
const outputFile = './final_wxapp_with_audio.mp4';

async function run() {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn(ffmpegPath, [
      '-y',
      '-i', videoInput,
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
      console.error(`stderr: ${data}`);
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        console.log(`Successfully merged video and audio into ${outputFile}`);
        resolve();
      } else {
        reject(new Error(`Process exited with code ${code}`));
      }
    });
  });
}

run().catch(console.error);
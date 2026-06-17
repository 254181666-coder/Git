const { spawn } = require('child_process');
const ffmpegPath = require('ffmpeg-static');

console.log('FFmpeg path:', ffmpegPath);

const inputFile = './a61a2225d3b33f34146f8c8fce3b8346.mov';
const startTime = '30';
const endTime = '210';
const speed = '2';
const outputFile = './speed_up_output.mp4';

const duration = parseInt(endTime) - parseInt(startTime);
const outputDuration = duration / parseFloat(speed);

console.log(`Processing video:`);
console.log(`- Input: ${inputFile}`);
console.log(`- Start: ${startTime}s`);
console.log(`- End: ${endTime}s`);
console.log(`- Duration: ${duration}s`);
console.log(`- Speed: ${speed}x`);
console.log(`- Expected output duration: ${outputDuration.toFixed(1)}s`);

async function run() {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn(ffmpegPath, [
      '-y',
      '-ss', startTime,
      '-to', endTime,
      '-i', inputFile,
      '-filter:v', `setpts=${1/parseFloat(speed)}*PTS`,
      '-filter:a', `atempo=${speed}`,
      '-c:v', 'libx264',
      '-crf', '23',
      '-c:a', 'aac',
      '-strict', 'experimental',
      outputFile
    ]);

    ffmpeg.stderr.on('data', (data) => {
      console.error(`stderr: ${data}`);
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        console.log(`Successfully created: ${outputFile}`);
        resolve();
      } else {
        reject(new Error(`Process exited with code ${code}`));
      }
    });
  });
}

run().catch(console.error);
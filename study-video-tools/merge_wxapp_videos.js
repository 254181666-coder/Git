const { spawn } = require('child_process');
const ffmpegPath = require('ffmpeg-static');

console.log('FFmpeg path:', ffmpegPath);

const video1Input = './小程序1.mov';
const video2Input = './小程序2.mp4';
const trimmedVideo1 = './trimmed_小程序1.mp4';
const resizedVideo1 = './resized_小程序1.mp4';
const outputFile = './merged_wxapp.mp4';

const trimStart = '1';
const trimEnd = '70';
const targetWidth = '1920';
const targetHeight = '960';

function trimVideo1() {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn(ffmpegPath, [
      '-y',
      '-ss', trimStart,
      '-to', trimEnd,
      '-i', video1Input,
      '-c:v', 'libx264',
      '-crf', '23',
      '-c:a', 'aac',
      '-strict', 'experimental',
      trimmedVideo1
    ]);

    ffmpeg.stderr.on('data', (data) => {
      console.error(`trim stderr: ${data}`);
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        console.log(`Successfully trimmed ${video1Input}`);
        resolve();
      } else {
        reject(new Error(`Trim process exited with code ${code}`));
      }
    });
  });
}

function resizeVideo1() {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn(ffmpegPath, [
      '-y',
      '-i', trimmedVideo1,
      '-vf', `scale=${targetWidth}:${targetHeight}:force_original_aspect_ratio=decrease,pad=${targetWidth}:${targetHeight}:(ow-iw)/2:(oh-ih)/2`,
      '-c:v', 'libx264',
      '-crf', '23',
      '-c:a', 'copy',
      resizedVideo1
    ]);

    ffmpeg.stderr.on('data', (data) => {
      console.error(`resize stderr: ${data}`);
    });

    ffmpeg.on('close', (code) => {
      if (code === 0) {
        console.log(`Successfully resized ${trimmedVideo1}`);
        resolve();
      } else {
        reject(new Error(`Resize process exited with code ${code}`));
      }
    });
  });
}

function mergeVideos() {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn(ffmpegPath, [
      '-y',
      '-i', resizedVideo1,
      '-i', video2Input,
      '-filter_complex', '[0:v][0:a][1:v]concat=n=2:v=1:a=1[v][a]',
      '-map', '[v]',
      '-map', '[a]',
      '-c:v', 'libx264',
      '-crf', '23',
      '-c:a', 'aac',
      '-strict', 'experimental',
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
        console.log('Trying fallback: video only');
        const ffmpegFallback = spawn(ffmpegPath, [
          '-y',
          '-i', resizedVideo1,
          '-i', video2Input,
          '-filter_complex', '[0:v][1:v]concat=n=2:v=1[v]',
          '-map', '[v]',
          '-c:v', 'libx264',
          '-crf', '23',
          outputFile
        ]);

        ffmpegFallback.stderr.on('data', (data) => {
          console.error(`fallback stderr: ${data}`);
        });

        ffmpegFallback.on('close', (fallbackCode) => {
          if (fallbackCode === 0) {
            console.log(`Successfully merged (video only) into ${outputFile}`);
            resolve();
          } else {
            reject(new Error(`Fallback merge process exited with code ${fallbackCode}`));
          }
        });
      }
    });
  });
}

async function run() {
  try {
    console.log('Step 1: Trimming 小程序1.mov...');
    console.log(`- Start: ${trimStart}s, End: ${trimEnd}s`);
    await trimVideo1();
    
    console.log('Step 2: Resizing video to match resolution...');
    console.log(`- Target: ${targetWidth}x${targetHeight}`);
    await resizeVideo1();
    
    console.log('Step 3: Merging videos...');
    await mergeVideos();
    
    console.log('All done!');
  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

run();
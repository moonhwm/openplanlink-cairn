import { media } from '@kit.MediaKit';
import { hilog } from '@kit.PerformanceAnalysisKit';

const TAG = 'StockPulse.AudioPlayer';
const DOMAIN = 0x0001;

/** 云端 TTS 音频流点按播报（适老化核心交互：点卡片=听） */
export class AudioPlayer {
  private static player: media.AVPlayer | null = null;

  /**
   * 播放音频流。
   * - onDone：播放完成（completed/idle 状态）时回调
   * - onError：播放出错（AVPlayer error 事件或 prepare/play reject）时回调
   * - Promise：prepare+play 成功时 resolve，失败时 reject
   */
  static async play(url: string, onDone?: () => void, onError?: () => void): Promise<void> {
    await AudioPlayer.stop();
    let av: media.AVPlayer;
    try {
      av = await media.createAVPlayer();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `createAVPlayer failed: ${(e as Error).message}`);
      onError?.();
      throw new Error((e as Error).message);
    }
    AudioPlayer.player = av;

    av.on('stateChange', (state: media.AVPlayerState) => {
      if (state === 'completed' || state === 'idle') {
        onDone?.();
      }
    });
    av.on('error', (err) => {
      hilog.warn(DOMAIN, TAG, `play error: ${err.message}`);
      onError?.();
    });

    av.url = url;
    try {
      await av.prepare();
      await av.play();
    } catch (e) {
      hilog.warn(DOMAIN, TAG, `prepare/play failed: ${(e as Error).message}`);
      // 清理半初始化的 player
      try {
        await av.release();
      } catch (e2) { /* 忽略重复释放 */ }
      AudioPlayer.player = null;
      onError?.();
      throw new Error((e as Error).message);
    }
  }

  static async stop(): Promise<void> {
    if (AudioPlayer.player) {
      try {
        await AudioPlayer.player.stop();
        await AudioPlayer.player.release();
      } catch (e) { /* 忽略重复释放 */ }
      AudioPlayer.player = null;
    }
  }
}

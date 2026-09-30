#include "lights.h"

char buf[BUF_SIZE];

int x, y;

int width, height;
png_byte color_type;
png_byte bit_depth;
png_byte color_channels;

png_structp png_ptr;
png_infop info_ptr;
int number_of_passes;
png_bytep * row_pointers;

int lights_auto;
int lights_running;

pthread_t t_run_lights;
pthread_mutex_t lights_mutex;


unsigned long long millis(){
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (unsigned long long)(tv.tv_sec) * 1000 + (unsigned long long)(tv.tv_usec) / 1000;
}

void abort_(const char * s, ...)
{
    va_list args;
    va_start(args, s);
    vfprintf(stderr, s, args);
    fprintf(stderr, "\n");
    va_end(args);
    // abort();
}

int read_png_file(char* file_name)
{
    unsigned char header[8];
    FILE *fp = fopen(file_name, "rb");
    if (!fp) {
        abort_("[read_png_file] File %s could not be opened for reading", file_name);
        return 1;
    }
    if (fread(header, 1, 8, fp) != 8 || png_sig_cmp(header, 0, 8)) {
        abort_("[read_png_file] File %s is not recognized as a PNG file", file_name);
        fclose(fp);
        return 1;
    }

    struct png_image {
        png_structp png;
        png_infop info;
        png_bytep *rows;
        int rows_allocated;
    } *next = calloc(1, sizeof(*next));
    if (!next) {
        fclose(fp);
        return 1;
    }

    next->png = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    if (!next->png) {
        abort_("[read_png_file] png_create_read_struct failed");
        goto failed;
    }
    next->info = png_create_info_struct(next->png);
    if (!next->info) {
        abort_("[read_png_file] png_create_info_struct failed");
        goto failed;
    }
    if (setjmp(png_jmpbuf(next->png))) {
        abort_("[read_png_file] Error reading %s", file_name);
        goto failed;
    }
    png_init_io(next->png, fp);
    png_set_sig_bytes(next->png, 8);
    png_read_info(next->png, next->info);
    int new_width = png_get_image_width(next->png, next->info);
    int new_height = png_get_image_height(next->png, next->info);
    int new_depth = png_get_bit_depth(next->png, next->info);
    int new_channels = png_get_channels(next->png, next->info);
    if (new_width < 1 || new_height < 1 || new_depth != 8 || new_channels < 3 ||
        (new_width == 4 && new_height < 3)) {
        abort_("[read_png_file] Unsupported dimensions or color in %s", file_name);
        goto failed;
    }
    png_set_interlace_handling(next->png);
    png_read_update_info(next->png, next->info);
    next->rows = calloc((size_t)new_height, sizeof(*next->rows));
    if (!next->rows) goto failed;
    for (int row = 0; row < new_height; row++) {
        next->rows[row] = malloc(png_get_rowbytes(next->png, next->info));
        if (!next->rows[row]) goto failed;
        next->rows_allocated++;
    }
    png_read_image(next->png, next->rows);

    for (int row = 0; row < height; row++) free(row_pointers[row]);
    free(row_pointers);
    row_pointers = next->rows;
    width = new_width;
    height = new_height;
    color_channels = new_channels;
    bit_depth = new_depth;
    color_type = png_get_color_type(next->png, next->info);
    next->rows = NULL;
    fclose(fp);
    png_destroy_read_struct(&next->png, &next->info, NULL);
    free(next);
    return 0;

failed:
    for (int row = 0; row < next->rows_allocated; row++) free(next->rows[row]);
    free(next->rows);
    png_destroy_read_struct(&next->png, &next->info, NULL);
    free(next);
    fclose(fp);
    return 1;
}

int initLights() {
    lights_auto = 1;

    bcm2835_init();
    bcm2835_spi_begin();
    bcm2835_spi_set_speed_hz(SPI_SPEED_HZ);
    bcm2835_spi_setDataMode(BCM2835_SPI_MODE0);
    bcm2835_spi_chipSelect(BCM2835_SPI_CS0);
    bcm2835_spi_setChipSelectPolarity(BCM2835_SPI_CS0, LOW);

    int x;
    for(x = 0; x < BUF_SIZE; x++){
        buf[x] = 0;
    }

    for(x = BUF_SIZE - SOF_BYTES; x < BUF_SIZE; x++){
        buf[x] = 255;
    }

    pthread_mutex_init ( &lights_mutex, NULL );

    return 0;
}

void *lights_run(void *void_ptr){
    while(lights_running){
        int delta = height ? (millis() / (1000/60)) % height : 0;
        if (lights_auto && height && row_pointers) {
            pthread_mutex_lock( &lights_mutex );
            lights_drawPngFrame(delta);
            pthread_mutex_unlock( &lights_mutex );
        }
        lights_show();
        usleep(16666); // About 60fps
    }
    return NULL;
}

int lights_start() {
    lights_running = 1;
    if(pthread_create(&t_run_lights, NULL, lights_run, NULL)) {
        lights_running = 0;
        printf("Error creating lighting thread.\n");
        return 1;
    }
    return 0;
}

void lights_lock() {
    pthread_mutex_lock(&lights_mutex);
}

void lights_unlock() {
    pthread_mutex_unlock(&lights_mutex);
}

int lights_getWidth() {
    return width;
}

int lights_getHeight() {
    return height;
}

void lights_stop() {
    lights_running = 0;
    pthread_join(t_run_lights, NULL);
}

void lights_setPixel(int x, int r, int g, int b){
    int offset = SOF_BYTES + (x * 4);
    buf[offset + 0] = 0b11100011;
    buf[offset + 1] = b;
    buf[offset + 2] = g;
    buf[offset + 3] = r;
}

void lights_setAll(int r, int g, int b){
    int x;
    for(x = 0; x < 12; x++){
        lights_setPixel(x, r, g, b);
    }
}

void lights_show(){
    bcm2835_spi_writenb(buf, BUF_SIZE);
    usleep(MIN_DELAY_US);
}

void lights_cleanup(){
    bcm2835_spi_end();
    bcm2835_close();
}

void lights_drawPngFrame(int frame){
    if(width == 4){
    /*
        4x3xN animation image,
        each 4x3 area represents a single frame.
    */
    frame = (frame % (height / 3)) * 3;
    for(y = 0; y < 3; y++){
        png_byte* row = row_pointers[frame + y];
        for(x = 0; x < 4; x++){
        png_byte* ptr = &(row[x * color_channels]);
        lights_setPixel(x + (y * 4), ptr[0], ptr[1], ptr[2]);
        // printf("x: %d, y: %d, xy: %d  ", x, y, x + (y*4));
        // printf("r: %d, g: %d, b: %d\n", ptr[0], ptr[1], ptr[2]);
        }
    }
    return;
    }
    /* 
    Other - will try to fit horizontal pixels to keys,
    wrapping where necessary.
    each vertical pixel is one frame
    */
    frame = frame % height;
    png_byte* row = row_pointers[frame];
    for(x = 0; x < 12; x++){
        int offset = (x % width) * color_channels;
        png_byte* ptr = &(row[offset]);
        lights_setPixel(x, ptr[0], ptr[1], ptr[2]);
    }
    return;
}

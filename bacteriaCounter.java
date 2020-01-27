import processing.core.*; 
import processing.data.*; 
import processing.event.*; 
import processing.opengl.*; 

import g4p_controls.*; 

import java.util.HashMap; 
import java.util.ArrayList; 
import java.io.File; 
import java.io.BufferedReader; 
import java.io.PrintWriter; 
import java.io.InputStream; 
import java.io.OutputStream; 
import java.io.IOException; 

public class bacteriaCounter extends PApplet {

//initiation page that allows loading of image into analysis window
PImage logo;
PImage titlebaricon;
//image to analyse
String startImg;
PImage workImg;
//image that will hold dot pixel colours
PImage shedImg;
int bhei = 180;
int bwid = 50;


//initiate variables and define splash page
public void setup() {
  //small window to load files from
  
  colorMode(RGB);
  background(255);
  logo = loadImage("data/logo.png");
  logo.resize(400,0);
  //set window title and icon
  surface.setTitle("BAC-COUNT");
  titlebaricon = loadImage("data/icon.png");
  surface.setIcon(titlebaricon);
  //place file select and quit buttons and set custom color scheme
  g4p_controls.G4P.setGlobalColorScheme(8);
  btnOpenFile = new GButton(this, bwid, bhei, 140, 20, "Select File");
  btnQuit = new GButton(this, 180+bwid, bhei, 140, 20, "Quit");
  GLabel verNum = new GLabel(this, 320+bwid, bhei-30, 140, 20, "v1.0.0");
}

//draw the splash page
public void draw(){
  background(255);
  image(logo, 10, 10);
}
//cross hair sizer
int cs=20;

//crop coords
int crop1x;
int crop1y;
int crop2x;
int crop2y;


//set control vars
boolean cropset=false;
boolean inArea=false;
boolean drawCrop=false;
//circular crop is true
boolean cropShape=true;

//controlling vars
boolean midCrop=false;

//function for cropping image
public void cropImg(PApplet app){
  int mx = app.mouseX;
  int my = app.mouseY;
   
  //get the croppable area
  int imgXend=workImg.width+((winwidth-workImg.width)/2);
  int imgXstart=(winwidth-workImg.width)/2;
  int imgYend=workImg.height+((winheight-workImg.height)/2);
  int imgYstart=(winheight-workImg.height)/2;
  
  //only active if cursor is in the croppable area
  if(mx>imgXstart && mx<imgXend && my>imgYstart && my<imgYend){
    //draw cropping cross-hair
    app.noCursor();
    app.stroke(125);
    app.line(mx-cs,my,mx+cs,my);
    app.line(mx,my-cs,mx,my+cs);
    //set area status
    inArea=true;
    //set cropping preview positions
    if(midCrop==true){
      crop2x=mx;
      crop2y=my;
    }
  }
  else{
    app.cursor();
    inArea=false;
  }
  
  //draw the croppable area
  if(drawCrop==true){
    app.noFill();
    app.stroke(125);
    //circle
    if(cropShape==true){
      app.ellipseMode(CENTER);
      app.circle(crop1x,crop1y,dist(crop1x,crop1y,crop2x,crop2y)*2);
    }//rect
    else{
      app.rectMode(CORNERS);
      app.rect(crop1x,crop1y,crop2x,crop2y);
      app.rectMode(CORNER);
    }
  }
  
}

//function to action cropping on mouse clicks
public void croppingCheck(int xpos, int ypos){
  if(inArea==true){
    if(midCrop==false){
      crop1x=xpos;
      crop1y=ypos;
      drawCrop=true;
      midCrop=true;
    }
    else{
      midCrop=false;
    }
  }
}

//function to carry out cropping (make pixels outside selected area black)
public void drawCrop(){
  //translate the global pixels to locations in the image
  int pix1x=crop1x-((winwidth-workImg.width)/2);
  int pix1y=crop1y-((winheight-workImg.height)/2);
  int pix2x=crop2x-((winwidth-workImg.width)/2);
  int pix2y=crop2y-((winheight-workImg.height)/2);
  
  //rectangular crop
  if(cropShape==false){
   for(int j=0; j<workImg.pixels.length; j++){
    int px = j % workImg.width;
    int py = j / workImg.width;
    if(px<min(pix1x,pix2x)||px>max(pix1x,pix2x)||py<min(pix1y,pix2y)||py>max(pix1y,pix2y)){
      workImg.pixels[j]=color(0,0,0);
    }
   }
  }
  
  //circular crop
  if(cropShape==true){
    for(int j=0; j<workImg.pixels.length; j++){
    int px = j % workImg.width;
    int py = j / workImg.width;
    if(abs(dist(pix1x,pix1y,px,py))>abs(dist(pix1x,pix1y,pix2x,pix2y))){
       workImg.pixels[j]=color(0,0,0);
    }
   }
  }
  
}

//function to turn cropping on/off
public void cropToggle(){
  if(cropactive==true){
    cropactive=false;
    btnSquareCrop.setEnabled(true);
    btnCircleCrop.setEnabled(true);
  }
  else{
    cropactive=true;
    btnSquareCrop.setEnabled(false);
    btnCircleCrop.setEnabled(false);
  }
}
IntList whitePixels = new IntList();

//function to return the image as a greyscale map of eucledian distances of white pixels from nearest black pixel
public PImage distanceMap(PImage threshedImg){
  PImage i = threshedImg;
  int white = color(255,255,255);
  int black = color(0,0,0);
  //find all the white and black pixels
  whitePixels = getCol(i,white);
  IntList blackPixels = getCol(i,black);
  float[] map = new float[whitePixels.size()];
  //find distances 
  for (int j = 0; j < map.length; j++) {
        map[j]=getDist(i,whitePixels.get(j),black);
  }
  //scale pixels greyscale value based on their distances, using the resolution parameter to determine number of different levels between the min and max
  float maxobs = max(map);
  float minobs = min(map);
  for(int j =0; j<map.length; j++){
    map[j]=round(map(map[j],minobs,maxobs,0,resolution));
  }
  maxobs = max(map);
  minobs = min(map);
  for(int j =0; j<map.length; j++){
    float val= round(map(map[j],minobs,maxobs,254,0));
    int ploc = whitePixels.get(j);
    i.pixels[ploc]=color(val,val,val);
  }
  for(int j=0; j<blackPixels.size(); j++){
    i.pixels[blackPixels.get(j)]=white;
  }
return(i);
}

//function to fetch all pixels of a given color (also used in watershed sort)
public IntList getCol(PImage i, int col){
  IntList pix = new IntList();
  for(int j=0; j < i.pixels.length; j++){
    if(i.pixels[j]==col){
      pix.append(j);
    }
  }
  return(pix);
}


//function to find the nearest black pixel, maintains speed by iteratively expanding a search square around a pixel
public float getDist(PImage i, int start_point, int col){
  float d = 0.0f;
  int sx = start_point % i.width;
  int sy = start_point / i.width;
  
  boolean whitefound = false;
  boolean scanend = false;
  //will scan all pixels within a grid with scansize*2 size sides
  int scansize = 5;
  int lastscan = 0;
  
  while(whitefound == false||scanend ==false){
    scanend=false;
    for(int nx=sx-scansize; nx<sx+scansize+1; nx++){
      //skip previously scanned pixels if extended since last scan
      if(nx<sx-lastscan||nx>sx+lastscan){
        for(int ny=sy-scansize; ny<sy+scansize+1; ny++){
          if(ny<sy-lastscan||ny>sy+lastscan){
            if(nx>=0&&nx<i.width&&ny>=0&&ny<i.height){
              int nloc=nx+(ny*i.width);
              if(i.pixels[nloc]==col){
                if(whitefound==false){
                  d=dist(sx,sy,nx,ny);
                  whitefound=true;
                }else{
                  float td=dist(sx,sy,nx,ny);
                  if(td<d){d=td;}
                }
              }
            }
          }
        }
      }
    }
    scanend=true;
    lastscan=scansize;
    //exapand scan area if no pixel found
    scansize+=10;
  }
  
  return(d);
  
}
int c0 = 0xff003DFF;
int c1 = 0xffFF0000;
int c2 = 0xffFFC000;
int c3 = 0xffE0FF00;
int c4 = 0xff7EFF00;
int c5 = 0xff21FF00;
int c6 = 0xff00FF41;
int c7 = 0xff00FF9F;
int c8 = 0xff00FDFF;
int c9 = 0xff009FFF;
int[] cols = {c0,c1,c2,c3,c4,c5,c6,c7,c8,c9};
int maxcol=cols.length;

//function to take the 'dots' found in the watershed algorithm and plot them with unique colors from the pallete above
public void drawShed(){  int curcol=0;
  IntDict colmap = new IntDict();
  for(int i=0; i<shedImg.pixels.length; i++){
    int pcatch=catchmentDefs[i];
    if(pcatch!=-2){
    if(colmap.hasKey(str(pcatch))){
      shedImg.pixels[i]=cols[colmap.get(str(pcatch))];
    }
    else{
      shedImg.pixels[i]=cols[curcol];
      colmap.set(str(pcatch),curcol);
      curcol+=1;
      if(curcol==maxcol){
        curcol=0;
      }  
    }
  }
  else{
    shedImg.pixels[i]=color(0,0,0);
  }
  }
}
//code to generate the main analysis window and handle the GUI controls


//Window size
int winwidth=800;
int winheight=550;

//GUI sections
int rgbstart = 10;
int cropstart = 210;
int threshstart = 400;
int mapstart = 550;
int watstart = 690;

//pop up window for the analysis
GWindow window;
int guihei = 180;

//splash buttons
GButton btnOpenFile;
GButton btnQuit;

//gui section headings
GLabel imagemod;
GLabel cropping;
GLabel thresholding;
GLabel distmapping;
GLabel watershed;

//RGB controls
GCheckbox rgbCheck;
GSlider redSlide;
GLabel redText;
GLabel redVal;
GSlider greenSlide;
GLabel greenText;
GLabel greenVal;
GSlider blueSlide;
GLabel blueText;
GLabel blueVal;
int redv = 255;
int greenv = 255;
int bluev = 255;
Boolean rgbon = false;

//greyscale mode
Boolean greyscale = false;
GCheckbox greyCheck;

//dilate mode
Boolean dilate = false;
GCheckbox dilCheck;

//crop controls
GButton btnCircleCrop;
GButton btnSquareCrop;
GButton btnCropConfirm;
GButton btnCropCancel;
Boolean cropactive = false;

//thresholding controls
GCheckbox threshCheck;
GSlider threshSlide;
GLabel threshText;
GLabel valLabel;
int threshval = 50;
Boolean threshon = false;

//map controls
GCheckbox mapCheck;
GSlider mapSlider;
boolean mapon = false;
GSlider resSlide;
int resolution = 10;
GLabel resLabel;
GLabel resText;

//asterisk label
GLabel asterisk;

//watershed (counting) controls
GButton watCount;
GCheckbox watCheck;
boolean waton = true;
boolean shedready = false;
GLabel countTitle;
GLabel countVal;
GButton addSection;
GButton clearSections;
boolean sectionactive=false;
GButton exportDat;


//controls for buttons
public void handleButtonEvents(GButton button, GEvent event) {
  //loading button from splash page
  if (button == btnOpenFile && event == GEvent.CLICKED) {
    selectInput("Select a file to process:", "fileSelected");
  }
  //quit button
  if (button == btnQuit && event == GEvent.CLICKED) {
    exit();
  }
  //circular crop
  if (button == btnCircleCrop && event == GEvent.CLICKED){
    cropShape=true;
    cropToggle();
  }
  //square crop
  if (button == btnSquareCrop && event == GEvent.CLICKED){
    cropShape=false;
    cropToggle();
  }
  //confirm a cropped area
   if (button == btnCropConfirm && event == GEvent.CLICKED){
    if(cropactive=true){
    cropToggle();
    if(midCrop==false && drawCrop==true){
      cropset=true;
      imageRefresh();
    }
    }
  }
  //cancel cropping
  if (button == btnCropCancel && event == GEvent.CLICKED){
    if(cropactive==true){
    cropToggle();
    crop1x=0;
    crop1y=0;
    crop2x=0;
    crop2y=0;
    }
    cropset=false;
    cropactive=false;
    imageRefresh();
  }
  //initiate calculation of watershed (dot counting)
  if (button == watCount && event == GEvent.CLICKED){
    watCount.setEnabled(false);
    watershedRun();
    countVal.setText(str(objCount));
    imageRefresh();
    watCount.setEnabled(true);
    watCount.setText("Re-count");
  }
  //section creation button
  if (button == addSection && event == GEvent.CLICKED){
    sectionactive=true;
  }
  //section clearing button
  if(button == clearSections && event == GEvent.CLICKED){
    clearSecs(true);
  }
    //export button
  if (button == exportDat && event == GEvent.CLICKED) {
    selectOutput("Select output destination:", "writeOutput");
  }
}

//toggle rgb filter with checkbox
public void rgbCheck_clicked(GCheckbox source, GEvent event) {
  if(source.isSelected()){
    rgbon=true;
  }
  else{
    rgbon=false;
  }
  imageRefresh();
}

//change tint based on rgb settings
public void redSlider_change(GSlider source, GEvent event) { 
  redv=round(source.getValueF());
  redVal.setText(str(redv));
  imageRefresh();
}
public void greenSlider_change(GSlider source, GEvent event) { 
  greenv=round(source.getValueF());
  greenVal.setText(str(greenv));
  imageRefresh();
}
public void blueSlider_change(GSlider source, GEvent event) { 
  bluev=round(source.getValueF());
  blueVal.setText(str(bluev));
  imageRefresh();
}

//toggle greyscale with checkbox
public void greyCheck_clicked(GCheckbox source, GEvent event) {
  if(source.isSelected()){
    greyscale=true;
  }
  else{
    greyscale=false;
  }
  imageRefresh();
}

//toggle dilate with checkbox
public void dilCheck_clicked(GCheckbox source, GEvent event) {
  if(source.isSelected()){
    dilate=true;
  }
  else{
    dilate=false;
  }
  imageRefresh();
}

//toggle threshold filter with checkbox
public void threshCheck_clicked(GCheckbox source, GEvent event) {
  if(source.isSelected()){
    threshon=true;
    mapCheck.setEnabled(true);
  }
  else{
    threshon=false;
    mapon=false;
    //can only carryout gradient mapping with threshold enabled
    mapCheck.setSelected(false);
    mapCheck.setEnabled(false);
    watCount.setEnabled(false);
  }
  imageRefresh();
}

//change threshold value based on slider value
public void threshSlider_change(GSlider source, GEvent event) { 
  threshval=round(source.getValueF());
  threshText.setText(str(threshval));
  imageRefresh();
}

//toggle gradient map display with checkbox
public void mapCheck_clicked(GCheckbox source, GEvent event) {
  if(source.isSelected()){
    mapon=true;
    //can only carryout watershed with gradient map enabled
    watCount.setEnabled(true);
  }
  else{
    mapon=false;
    watCount.setEnabled(false);
  }
  imageRefresh();
}

//change mapping resolution value based on slider value
public void resSlider_change(GSlider source, GEvent event) { 
  resolution=round(source.getValueF());
  resText.setText(str(resolution));
  imageRefresh();
}

//toggle drawing of counted dots with checkbox
public void watCheck_clicked(GCheckbox source, GEvent event) {
  if(source.isSelected()){
    waton=true;
  }
  else{
    waton=false;
  }
  imageRefresh();
}


//function to initiate an analysis window after selecting a file
//specifies location of all GUI elements
public void fileSelected(File selection) {
  if (selection == null) {
  } else {
    startImg = selection.getAbsolutePath();
    //make working image a reasonable size and add space for gui at the bottom
    imageRefresh();
    
    //generate working window
    window=GWindow.getWindow(this, "Dot: "+startImg, 100, 50, winwidth, winheight+guihei, JAVA2D);
    window.addDrawHandler(this, "windowDraw");
    window.addMouseHandler(this, "windowMouse");
    window.addOnCloseHandler(this, "windowClose");
    //set close window actions as defined in windowDraw
    window.setActionOnClose(G4P.CLOSE_WINDOW);    
    
    //disable file opener as can only work on one image at a time
    btnOpenFile.setEnabled(false);

    //add controls to gui area
    int guistart=winheight+30;
    
    //RGB controls
    imagemod = new GLabel(window,rgbstart,guistart-25,200,20);
    imagemod.setText("1. Image Adjustments");
    imagemod.setTextBold();
    rgbCheck = new GCheckbox(window,rgbstart,guistart,150,20,"RGB Filter");
    rgbCheck.addEventHandler(this, "rgbCheck_clicked");
    rgbCheck.setSelected(false);
    if(rgbon==true){rgbCheck.setSelected(true);}
    redText = new GLabel(window, rgbstart, guistart+25,80,20);
    redText.setText("Red:");
    redSlide = new GSlider(window, rgbstart+50, guistart+25, 75,20,10.0f);
    redSlide.setLimits(0,255);
    redSlide.setValue(redv);
    redSlide.addEventHandler(this, "redSlider_change");
    redVal = new GLabel(window, rgbstart+130, guistart+25,80,20);
    redVal.setText(str(redv));
    greenText = new GLabel(window, rgbstart, guistart+40,80,20);
    greenText.setText("Green:");
    greenSlide = new GSlider(window, rgbstart+50, guistart+40, 75,20,10.0f);
    greenSlide.setLimits(0,255);
    greenSlide.setValue(greenv);
    greenSlide.addEventHandler(this, "greenSlider_change");
    greenVal = new GLabel(window, rgbstart+130, guistart+40,80,20);
    greenVal.setText(str(greenv));
    blueText = new GLabel(window, rgbstart, guistart+55,80,20);
    blueText.setText("Blue:");
    blueSlide = new GSlider(window, rgbstart+50, guistart+55, 75,20,10.0f);
    blueSlide.setLimits(0,255);
    blueSlide.setValue(bluev);
    blueSlide.addEventHandler(this, "blueSlider_change");
    blueVal = new GLabel(window, rgbstart+130, guistart+55,80,20);
    blueVal.setText(str(bluev));
    
    //greyscale controls
    greyCheck=new GCheckbox(window,rgbstart,guistart+80,80,20,"Greyscale");
    greyCheck.addEventHandler(this, "greyCheck_clicked");
    greyCheck.setSelected(false);
    if(greyscale==true){greyCheck.setSelected(true);}
    
    //dilate controls
    dilCheck=new GCheckbox(window,rgbstart+90,guistart+80,80,20,"Dilate");
    dilCheck.addEventHandler(this, "dilCheck_clicked");
    dilCheck.setSelected(false);
    if(dilate==true){dilCheck.setSelected(true);}
    
    //cropping controls
    cropping=new GLabel(window,cropstart,guistart-25,200,20);
    cropping.setText("2. Image Cropping");
    cropping.setTextBold();
    btnCircleCrop = new GButton(window, cropstart, guistart, 140, 20, "Circular");
    btnSquareCrop = new GButton(window, cropstart, guistart+25, 140, 20, "Rectangular");
    btnCropConfirm = new GButton(window, cropstart, guistart+50, 65, 20, "Confirm");
    btnCropCancel = new GButton(window, cropstart+75, guistart+50, 65, 20, "Clear");
    
    //thresholding controls
    thresholding = new GLabel(window,threshstart,guistart-25,150,20);
    thresholding.setText("3. Thresholding*");
    thresholding.setTextBold();
    threshCheck=new GCheckbox(window,threshstart,guistart,100,20,"On/Off");
    threshCheck.addEventHandler(this, "threshCheck_clicked");
    threshCheck.setSelected(false);
    valLabel=new GLabel(window,threshstart,guistart+20,120,20);
    valLabel.setText("Threshold:");
    threshText=new GLabel(window,threshstart+70,guistart+20,50,20);
    threshText.setText(str(threshval));
    threshSlide = new GSlider(window,threshstart,guistart+40, 90, 20, 10.0f);
    threshSlide.addEventHandler(this, "threshSlider_change");
    threshSlide.setLimits(0,100);
    threshSlide.setValue(threshval);
    
    //asterisk note
    asterisk = new GLabel(window,threshstart,guistart+125,300,30);
    asterisk.setText("*must be set before counting");
    
    //graident map controls
    distmapping = new GLabel(window,mapstart,guistart-25,150,20);
    distmapping.setText("4. Dist. Map*");
    distmapping.setTextBold();
    mapCheck=new GCheckbox(window,mapstart,guistart,90,20,"On/Off");
    mapCheck.addEventHandler(this, "mapCheck_clicked");
    mapCheck.setSelected(false);
    mapCheck.setEnabled(false);
    resLabel=new GLabel(window,mapstart,guistart+20,120,20);
    resLabel.setText("Resolution:");
    resText=new GLabel(window,mapstart+70,guistart+20,50,20);
    resText.setText(str(resolution));
    resSlide = new GSlider(window,mapstart,guistart+40, 90, 20, 10.0f);
    resSlide.addEventHandler(this, "resSlider_change");
    resSlide.setLimits(2,25);
    resSlide.setValue(resolution);
    
    
    //calc watershed/dot counting controls
    watershed = new GLabel(window,watstart,guistart-25,150,20);
    watershed.setText("5. Counting");
    watershed.setTextBold();
    watCount = new GButton(window, watstart, guistart, 100, 20, "Count");
    watCount.setEnabled(false);
    watCheck=new GCheckbox(window,watstart,guistart+25,150,20,"Show Dots?");
    watCheck.addEventHandler(this, "watCheck_clicked");
    watCheck.setSelected(true);
    watCheck.setEnabled(true);
    countTitle = new GLabel(window,watstart, guistart+45,50,20);
    countTitle.setText("Total:");
    countTitle.setTextBold();
    countVal = new GLabel(window,watstart+80, guistart+45,60, 20);
    countVal.setText(str(objCount));
    addSection = new GButton(window, watstart, guistart+70, 100, 20, "Add Section");
    clearSections = new GButton(window, watstart, guistart+95, 100, 20, "Clear Sections");
    exportDat = new GButton(window, watstart, guistart+125, 100, 20, "Export");
    exportDat.setTextBold();
  }
}
//function controlling what is displayed as the work image 
//order of events is important here e.g. watershed must be calculated on the thresholded image
public void imageRefresh(){
  workImg=loadImage(startImg);
  if(workImg.width>winwidth){
    workImg.resize(winwidth,0);
  }
  if(workImg.height>winheight){
    workImg.resize(0,winheight);
  }
  if(cropset==true){
    drawCrop();
  }
  shedImg=new PImage(workImg.width,workImg.height);
  if(rgbon==true){
    workImg=rgbFilter(workImg,redv,greenv,bluev);
  }
  if(dilate==true){
    workImg.filter(DILATE);
  }
  if(greyscale==true){
    workImg.filter(GRAY);
  }
  if(threshon==true){
    workImg.filter(THRESHOLD, threshval/100.0f);
  }
  if(mapon==true){
    workImg=distanceMap(workImg);
  }
  //only draw dots if the watershed calculation has completed
  if(waton==true && shedready==true){
    drawShed();
  }
}
//function to set variable on off status to defaults for example if loading another image
//dont reset values though, might want to carry settings across to another image
public void resetVars(){
     
  //thresholding
  threshon=false;
  threshCheck.setSelected(false);
  
  //gradient mapping
  mapon=false;
  mapCheck.setSelected(false);
  
  //watershed
  watCount.setText("Count");
  shedready=false;
  objCount=0; 
  
  //sections
  clearSecs(false);
  
}
//function to carry out basic RGB filtering of the image
public PImage rgbFilter(PImage img,int rval,int gval,int bval){
  for (int x = 0; x < img.width; x++) {
  for (int y = 0; y < img.height; y++ ) {
    // Calculate the 1D pixel location
    int loc = x + y*img.width;
    //get current values
    float cr = red (img.pixels[loc]);
    float cg = green (img.pixels[loc]);
    float cb = blue (img.pixels[loc]);
    if(cr>rval){cr=rval;}
    if(cg>gval){cg=gval;}
    if(cb>bval){cb=bval;}
    // Make a new color and set pixel in the window
    int c = color(cr,cg,cb);
    img.pixels[loc] = c;
    }
  }
  return(img);
}
//variables to control interface when selecting a new section
boolean midSection = false;
boolean drawSection = false;

//store the section coordinates, names and dot counts
ArrayList<int[]> sectionList = new ArrayList<int[]>();
ArrayList<String> sectionNames = new ArrayList<String>();
ArrayList<Integer> sectionCounts = new ArrayList<Integer>();

//coordinates when selections sections
int sec1x;
int sec2x;
int sec1y;
int sec2y;

//store the section data
public void makeSection(){
  int maxsec = sectionNames.size();
  int[] coords = {sec1x,sec1y,sec2x,sec2y};
  sectionList.add(coords);
  sectionNames.add("Sec_"+str(maxsec+1));
  sectionCounts.add(0);
  drawSection=false;
  sectionactive=false;
  if(objCount>0){
    countSecs(sectionNames.size()-1);
  }
}

//count number of dots in a section
public void countSecs(int sec){
  //convert coordinates to image space (from window space)
  int[] coords = sectionList.get(sec);
  int pix1x=coords[0]-((winwidth-workImg.width)/2);
  int pix1y=coords[1]-((winheight-workImg.height)/2);
  int pix2x=coords[2]-((winwidth-workImg.width)/2);
  int pix2y=coords[3]-((winheight-workImg.height)/2);
  
  //list to store what dots we see in the section
  ArrayList<Integer> dots = new ArrayList<Integer>();
  
  //parse the pixels in the section and count unique dots
  for(int i=min(pix1x,pix2x); i<max(pix1x,pix2x);i++){
    for(int j=min(pix1y,pix2y); j<max(pix1y,pix2y);j++){
      int loc = i + j*workImg.width;
      int val = catchmentDefs[loc];
      if(dots.contains(val)){}
     else if(val!=-2){dots.add(val);}
    }
  }
  
  //add count to list
  sectionCounts.set(sec,dots.size());
}

//draw the borders of defined sections onto the image
public void drawSections(PApplet app){
   for(int i=0; i<sectionNames.size(); i++){
     String name = sectionNames.get(i);
     int count = sectionCounts.get(i);
     int[] coords = sectionList.get(i);
     app.noFill();
     app.stroke(180);
     app.rectMode(CORNERS);
     app.rect(coords[0],coords[1],coords[2],coords[3]);
     app.rectMode(CORNER);
     app.fill(180);
     app.textSize(12);
     app.text(name+" "+str(count),min(coords[0],coords[2]),min(coords[1],coords[3])+10);
   }
}

//clear all sections
public void clearSecs(boolean fullwipe){
if(fullwipe==false){
for(int i=0; i<sectionCounts.size();i++){
  sectionCounts.set(i,0);
}
}
else{
sectionList = new ArrayList<int[]>();
sectionNames = new ArrayList<String>();
sectionCounts = new ArrayList<Integer>();
}
midSection = false;
drawSection = false;
sectionactive=false;
}

//function for selection of sections of image
public void selSection(PApplet app){
  int mx = app.mouseX;
  int my = app.mouseY;
   
  //get the area of the image in the window space
  int imgXend=workImg.width+((winwidth-workImg.width)/2);
  int imgXstart=(winwidth-workImg.width)/2;
  int imgYend=workImg.height+((winheight-workImg.height)/2);
  int imgYstart=(winheight-workImg.height)/2;
  
  //only active if cursor is in the image area
  if(mx>imgXstart && mx<imgXend && my>imgYstart && my<imgYend){
    //draw cross-hair
    app.noCursor();
    app.stroke(125);
    app.line(mx-cs,my,mx+cs,my);
    app.line(mx,my-cs,mx,my+cs);
    //set area status
    inArea=true;
    //set preview positions
    if(midSection==true){
      sec2x=mx;
      sec2y=my;
    }
  }
  //turn the cursor on and off with the cross hair
  else{
    app.cursor();
    inArea=false;
  }
  //if active draw where the section would be to current mouse position
  if(drawSection==true){
    app.noFill();
    app.stroke(125);
    app.rectMode(CORNERS);
    app.rect(sec1x,sec1y,sec2x,sec2y);
    app.rectMode(CORNER); 
  }
}


//function to action section selection on mouse clicks
public void sectionCheck(int xpos, int ypos, PApplet app){
  if(inArea==true){
    //if in middle of section definition
    if(midSection==false){
      sec1x=xpos;
      sec1y=ypos;
      drawSection=true;
      midSection=true;
    }
    else{
      makeSection();
      midSection=false;
      app.cursor();
    }
  }
}
//the watershed function is used to find the 'dots' in the image - using the pointer based algorithm from Bieniek & Moga 2000
//this is based on using a gradient map of the distances between black and white pixels and finding the local minima by following pointers between neighbouring pixels
int[] point;
int[] catchmentDefs;
int objCount =0;

//control overall watershed calculation
public void watershedRun(){
  point=new int[workImg.pixels.length];
  firstPass(whitePixels);
  secondPass(whitePixels);
  thirdPass(whitePixels);
  fourthPass(whitePixels);
  //relabel pixels to their dots
  catchmentDefs=reLabel(point);
  //get total dot count
  objCount=max(catchmentDefs);
  shedready=true;
  //if sections have been defined, count their dots
  if(sectionNames.size()>0){
    for(int i=0; i<sectionNames.size();i++){
      countSecs(i);
    }
  }
}

//function to generate the final labels numbered 1 to n dots
public int[] reLabel(int[] curlab){
  IntDict mapping = new IntDict();
  int[] newlabs = new int[curlab.length];
  int label=1;
  for(int i=0; i<curlab.length; i++){
    if(whitePixels.hasValue(i)==false){
      newlabs[i]=-2;
    }
    else{
      int cur=curlab[i];
      if(mapping.hasKey(str(cur))){
        newlabs[i]=mapping.get(str(cur));
      }
      else{
        newlabs[i]=label;
        mapping.set(str(cur),label);
        label+=1;
      }
    }
  }
  return(newlabs);
}


//run a rainfall algorithm for watershed segmentation (Bieniek & Moga 2000, Kornilov & Safonov 2018)
//first pass to set pointers for each pixel to lowest neighbouring pixel
public void firstPass(IntList whitePixels){
  for(int j=0; j<whitePixels.size(); j++){
    int p = whitePixels.get(j);
    int q=p;
    IntList neis = getNeighbours(workImg,p);
    for(int k=0; k<neis.size();k++){
      if(red(workImg.pixels[neis.get(k)])<red(workImg.pixels[p])){
        if(red(workImg.pixels[neis.get(k)])<red(workImg.pixels[q])){
          q=neis.get(k);
        }
      }
    }
    if(q!=p){point[p]=q;}
    else{point[p]=-1;}
  }
}

//second pass to remove non-minimal plateaus
public void secondPass(IntList whitePixels){
  IntList fifo = new IntList();
  //add plateau neighbouts with matching vals to the fifo
  for(int j=0; j<whitePixels.size(); j++){
    int p = whitePixels.get(j);
    //if a plateau parse
    if(point[p]==-1){
      IntList neis=getNeighbours(workImg,p);
      for(int k=0; k<neis.size();k++){
        //if not a plateu and same value as p
        if(point[neis.get(k)]!=-1 && red(workImg.pixels[neis.get(k)])==red(workImg.pixels[p])){
          fifo.append(neis.get(k));
          break;
      }
    }
  }
  }
  
  //fifo parsing
  while(fifo.size()!=0){
    int pf=fifo.remove(0);
    IntList neisf=getNeighbours(workImg,pf);
    for(int k=0; k<neisf.size(); k++){
      if(point[neisf.get(k)]==-1 && workImg.pixels[neisf.get(k)]==workImg.pixels[pf]){
        point[neisf.get(k)]=pf;
        fifo.append(neisf.get(k));
      }
    }
  }
}

//third pass mark the minimum plateaus to point to self
public void thirdPass(IntList whitePixels){
  for(int j=0; j<whitePixels.size(); j++){
    int p = whitePixels.get(j);
    if(point[p]==-1){
      point[p]=p;
      IntList neis=getNeighbours(workImg,p);
      for(int k=0; k<neis.size(); k++){
        //add an additional rule here that must be same altitude (greyscale value) (this is missing in the Bieniek & Moga pseudocode)
        if(neis.get(k)<p && red(workImg.pixels[neis.get(k)])==red(workImg.pixels[p])){
          int r=find(p);
          int r2=find(neis.get(k));
          int minv = min(r,r2);
          point[r]=minv;
          point[r2]=minv;
        }
      }
    }
  }
}

//final scan
public void fourthPass(IntList whitePixels){
  for(int j=0; j<whitePixels.size(); j++){
    int p = whitePixels.get(j);
    point[p]=find(p);
  }
}

//function that follows the path of pointers to find minima
public int find(int u){
  int r=u;
  while(point[r]!=r){
    r=point[r];
  }
  int w=u;
  int tmp=point[w];
  while(w!=r){
    tmp=point[w];
    point[w]=r;
    w=tmp;
  }
  return(r);
}

//function to grab the neighbouring pixels (8 surrounding)
public IntList getNeighbours(PImage i, int loc){
  IntList neis = new IntList();
  int lx = loc % i.width;
  int ly = loc / i.width;
  for(int j=lx-1; j<lx+2; j++){
    for(int k=ly-1; k<ly+2; k++){
      //dont include starting point in the neighbour list
      if(lx==j && ly==k){}
      //account for edge cases
      else if(j>=0 && j<i.width && k>=0 && k<i.height){
        int nloc=j+(k*i.width);
        if(whitePixels.hasValue(nloc)){
        neis.append(nloc);}
      }
    }
  }
  neis.sort();
  return(neis);
}
//function to draw to working window
public void windowDraw(PApplet app, GWinData data){
    app.background(0);
    //white box for the GUI elements
    app.fill(255);
    app.rect(0,window.height-guihei,window.width,guihei);
    app.image(workImg,(window.width-workImg.width)/2,((window.height-guihei)-workImg.height)/2);
    if(waton==true && shedready==true){
     app.image(shedImg,(window.width-workImg.width)/2,((window.height-guihei)-workImg.height)/2);
    }
    //draw crop and section markers if selection mode is active
    if(cropactive==true){
      cropImg(app);
    }
    else if(sectionactive==true){
      selSection(app);
    }
    //draw the sections on if any have been selected
  if(sectionNames.size()>0){
    drawSections(app);
  }
  //export the processed image
  if(exportImage==true){
    int tlx=(winwidth-workImg.width)/2;
    int tly=((window.height-guihei)-workImg.height)/2;
    PImage procImg = app.get(tlx,tly,workImg.width,workImg.height);
    procImg.save(outfile+".jpg");
    exportImage=false;  
}
}

//handler for clicks in the window, required for no GUI events
public void windowMouse(PApplet app, GWinData data, MouseEvent event){
    if(event.getAction() == MouseEvent.CLICK){
      if(cropactive==true&&sectionactive==false){
      croppingCheck(app.mouseX,app.mouseY);}
      else if(sectionactive==true){
      sectionCheck(app.mouseX,app.mouseY,app);}
    }
}

//handler for actions on window close
public void windowClose(GWindow window){
  //reenable file open button
  btnOpenFile.setEnabled(true);
  //reset variables
  resetVars();
}
boolean exportImage=false;
String outfile;

//write out a text file with the parameters used and the resultant counts for total and any sub sections
public void writeOutput(File selection){
  if (selection == null) {
  } else {
    //write out a csv of the results
    outfile = selection.getAbsolutePath();
    PrintWriter output = createWriter(outfile+".csv");
    output.println("Filename:,"+outfile);
    output.println("\nTotal Count:,"+str(objCount));
    output.println("\nSection Counts");
    for(int i=0; i<sectionNames.size(); i++){
    output.println(sectionNames.get(i)+":,"+str(sectionCounts.get(i)));
    }
    output.println("\nCount Settings");
    output.println("RGB Filter:,"+str(rgbon));
    output.println("RGB Vals:,"+str(redv)+"-"+str(greenv)+"-"+str(bluev));
    output.println("Greyscale:,"+str(greyscale));
    output.println("Dilate:,"+str(dilate));
    output.println("Image Cropped:,"+str(cropset));
    output.println("Threshold:,"+str(threshval));
    output.println("Resolution:,"+str(resolution));
    output.flush();
    output.close();
    //export image
    exportImage=true;
  }
}
  public void settings() {  size(420,210); }
  static public void main(String[] passedArgs) {
    String[] appletArgs = new String[] { "bacteriaCounter" };
    if (passedArgs != null) {
      PApplet.main(concat(appletArgs, passedArgs));
    } else {
      PApplet.main(appletArgs);
    }
  }
}
